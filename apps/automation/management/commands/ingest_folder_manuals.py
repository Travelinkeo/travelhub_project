import logging
import os
import zipfile

from defusedxml.ElementTree import fromstring
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.automation.services.rag_service import RAGKnowledgeService
from core.models import Agencia

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Indexa y vectoriza todos los manuales y documentos (PDF, DOCX, TXT) de una carpeta en la Base de Conocimiento RAG."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=str,
            default="/app/docs/manuales_gds",
            help="Ruta de la carpeta a escanear (default: /app/docs/manuales_gds)",
        )
        parser.add_argument(
            "--agencia-id",
            type=int,
            default=2,
            help="ID de la agencia a asociar los documentos (default: 2 - Travelinkeo)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Modo simulación: Muestra qué archivos procesaría sin guardar vectores",
        )

    def extract_docx_text(self, filepath: str) -> str:
        """Extrae texto de un archivo .docx leyendo su XML interno sin dependencias externas."""
        try:
            with zipfile.ZipFile(filepath) as z:
                xml_content = z.read("word/document.xml")
                tree = fromstring(xml_content)
                paragraphs = []
                for elem in tree.iter():
                    if elem.tag.endswith("}p"):
                        p_text = "".join([node.text for node in elem.iter() if node.text])
                        if p_text.strip():
                            paragraphs.append(p_text.strip())
                return "\n\n".join(paragraphs)
        except Exception as e:
            logger.warning(f"Error extrayendo texto DOCX {filepath}: {e}")
            return ""

    def extract_pdf_text(self, filepath: str) -> str:
        """Extrae texto de un archivo PDF usando pypdf."""
        try:
            import pypdf

            reader = pypdf.PdfReader(filepath)
            pages_text = []
            for page in reader.pages:
                t = page.extract_text()
                if t and t.strip():
                    pages_text.append(t.strip())
            return "\n\n".join(pages_text)
        except Exception as e:
            logger.warning(f"Error extrayendo texto PDF {filepath}: {e}")
            return ""

    def infer_gds_type(self, filepath: str) -> str:
        """Infiere el tipo de GDS según el nombre o ruta del archivo."""
        f_lower = filepath.lower()
        if "sabre" in f_lower:
            return "SABRE"
        elif "amadeus" in f_lower:
            return "AMADEUS"
        elif "kiu" in f_lower:
            return "KIU"
        elif "travelport" in f_lower or "galileo" in f_lower:
            return "TRAVELPORT"
        return "GENERAL"

    def handle(self, *args, **options):
        target_dir = options["dir"]
        agencia_id = options["agencia_id"]
        dry_run = options["dry_run"]

        self.stdout.write(
            self.style.SUCCESS(f"🚀 Escaneando manuales y documentos en: {target_dir}...")
        )

        try:
            agencia = Agencia.objects.get(id=agencia_id)
        except Agencia.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ La agencia con ID {agencia_id} no existe."))
            return

        if not os.path.exists(target_dir):
            self.stdout.write(self.style.ERROR(f"❌ La carpeta {target_dir} no existe."))
            return

        stats = {"scanned": 0, "processed": 0, "skipped": 0, "chunks": 0, "errors": 0}

        for root, _, files in os.walk(target_dir):
            for file in files:
                stats["scanned"] += 1

                # Omitir archivos temporales de Office o no soportados
                if file.startswith("~$") or file.startswith("."):
                    stats["skipped"] += 1
                    continue

                filepath = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()

                if ext not in [".pdf", ".docx", ".txt", ".md"]:
                    stats["skipped"] += 1
                    continue

                gds_type = self.infer_gds_type(filepath)
                title = os.path.splitext(file)[0].replace("_", " ").title()

                from django.apps import apps

                KBDocument = apps.get_model("cms", "KBDocument")

                # Comprobar si ya fue indexado en KBDocument
                if KBDocument.objects.filter(
                    agencia=agencia, title=title, is_indexed=True
                ).exists():
                    stats["skipped"] += 1
                    continue

                self.stdout.write(f"📄 Procesando: [{gds_type}] {title}...")

                text_content = ""
                if ext == ".pdf":
                    text_content = self.extract_pdf_text(filepath)
                elif ext == ".docx":
                    text_content = self.extract_docx_text(filepath)
                elif ext in [".txt", ".md"]:
                    try:
                        with open(filepath, encoding="utf-8", errors="ignore") as f:
                            text_content = f.read()
                    except Exception as e:
                        logger.warning(f"Error leyendo TXT/MD {filepath}: {e}")

                if not text_content or len(text_content.strip()) < 50:
                    self.stdout.write(
                        self.style.WARNING(f" ⚠️ Texto insuficiente en {file} (Omitido)")
                    )
                    stats["skipped"] += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f" [DRY-RUN] Vectorizaría '{title}' ({len(text_content)} caracteres)"
                    )
                    stats["processed"] += 1
                    continue

                try:
                    # Guardar registro KBDocument
                    doc, _ = KBDocument.objects.get_or_create(
                        agencia=agencia,
                        title=title,
                        defaults={
                            "gds_type": gds_type,
                            "descripcion": f"Importado desde carpeta local: {file}",
                        },
                    )

                    # Segmentar e indexar chunks en RAG
                    chunks = RAGKnowledgeService.chunk_text(text_content, max_chunk_size=500)
                    chunks_count = 0

                    from django.apps import apps

                    KnowledgeChunk = apps.get_model("cms", "KnowledgeChunk")

                    for idx, chunk in enumerate(chunks):
                        vec = RAGKnowledgeService.generate_embedding(chunk, agency=agencia)

                        KnowledgeChunk.objects.create(
                            agencia=agencia,
                            source_type="MANUAL_GDS",
                            source_title=f"{title} (Parte {idx + 1}/{len(chunks)})",
                            source_reference_id=doc.title,
                            content_chunk=chunk,
                            embedding_vector=vec,
                        )
                        chunks_count += 1

                    doc.is_indexed = True
                    doc.indexed_at = timezone.now()
                    doc.save()

                    stats["processed"] += 1
                    stats["chunks"] += chunks_count
                    self.stdout.write(
                        self.style.SUCCESS(f" ✅ Indexado: '{title}' ({chunks_count} chunks)")
                    )

                except Exception as e_proc:
                    self.stdout.write(self.style.ERROR(f" ❌ Error en '{title}': {e_proc}"))
                    stats["errors"] += 1

        self.stdout.write(self.style.SUCCESS("\n📊 RESUMEN DE INDEXACIÓN DE MANUALES LOCALES:"))
        self.stdout.write(f" - Archivos escaneados: {stats['scanned']}")
        self.stdout.write(f" - Manuales procesados e indexados: {stats['processed']}")
        self.stdout.write(f" - Chunks vectoriales creados: {stats['chunks']}")
        self.stdout.write(f" - Archivos omitidos/ya existentes: {stats['skipped']}")
        self.stdout.write(f" - Errores: {stats['errors']}")

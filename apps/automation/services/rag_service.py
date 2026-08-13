import logging
import math
import re
from typing import Any

from django.apps import apps
from django.utils import timezone

from apps.automation.services.ai_engine import _get_genai
from core.api import get_current_agency

logger = logging.getLogger(__name__)


class RAGKnowledgeService:
    """
    Servicio Central de RAG (Retrieval-Augmented Generation) y Vector Embeddings.
    Permite indexar y buscar información de Wikis, Manuales PDF (Sabre, Amadeus, KIU)
    y Correos informativos del Mailbot.
    """

    @classmethod
    def _get_chunk_model(cls):
        """Retorna dinámicamente el modelo KnowledgeChunk de la app CMS."""
        return apps.get_model("cms", "KnowledgeChunk")

    @classmethod
    def generate_embedding(cls, text: str, agency=None) -> list[float]:
        """
        Genera vector embeddings (text-embedding-004) mediante Google Gemini SDK.
        """
        if not text or not text.strip():
            return []

        try:
            client = _get_genai(agency=agency)
            response = client.models.embed_content(
                model="text-embedding-004",
                contents=text[:2048],  # Límite seguro de caracteres por chunk
            )
            if hasattr(response, "embedding") and hasattr(response.embedding, "values"):
                return list(response.embedding.values)
            elif isinstance(response, dict) and "embedding" in response:
                return response["embedding"].get("values", [])
            elif hasattr(response, "embeddings") and response.embeddings:
                return list(response.embeddings[0].values)
        except Exception as e:
            logger.warning(f"RAG: Error generando embedding Gemini para chunk: {e}")

        # Fallback determinístico de embeddings si la API falla
        return cls._fallback_vector(text)

    @classmethod
    def _fallback_vector(cls, text: str, dim: int = 768) -> list[float]:
        """Genera un vector hash determinístico si no hay conexión con Gemini."""
        import hashlib

        vector = [0.0] * dim
        words = re.findall(r"\w+", text.lower())
        if not words:
            return vector

        for word in words:
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            vector[idx] += 1.0

        # Normalizar L2
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector

    @classmethod
    def cosine_similarity(cls, vec_a: list[float], vec_b: list[float]) -> float:
        """Calcula la similitud de coseno entre dos vectores n-dimensionales."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    @classmethod
    def chunk_text(cls, text: str, max_chunk_size: int = 800) -> list[str]:
        """Divide texto largo en bloques de semántica continua."""
        if not text:
            return []

        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_length = 0

        for p in paragraphs:
            p_len = len(p)
            if current_length + p_len > max_chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [p]
                current_length = p_len
            else:
                current_chunk.append(p)
                current_length += p_len

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        return [c.strip() for c in chunks if c.strip()]

    @classmethod
    def index_kb_article(cls, article: Any) -> int:
        """Indexa un artículo de la Wiki / KBArticle en la base RAG."""
        KnowledgeChunk = cls._get_chunk_model()

        # Limpiar fragmentos previos de esta referencia
        KnowledgeChunk.objects.filter(
            source_type="WIKI", source_reference_id=str(article.id)
        ).delete()

        chunks = cls.chunk_text(f"{article.title}\n\n{article.content}")
        indexed_count = 0

        for chunk in chunks:
            vector = cls.generate_embedding(chunk, agency=article.agencia)
            KnowledgeChunk.objects.create(
                agencia=article.agencia,
                source_type="WIKI",
                source_title=article.title,
                source_reference_id=str(article.id),
                content_chunk=chunk,
                embedding_vector=vector,
            )
            indexed_count += 1

        logger.info(f"RAG: Indexado KBArticle '{article.title}' ({indexed_count} chunks)")
        return indexed_count

    @classmethod
    def index_pdf_manual(cls, document: Any, file_path: str | None = None) -> int:
        """Extrae texto e indexa un manual PDF de GDS en la base RAG."""
        pdf_path = file_path or (document.archivo_pdf.path if document.archivo_pdf else None)
        if not pdf_path:
            logger.error(f"RAG: Documento {document.id} no tiene ruta de archivo válida.")
            return 0

        extracted_text = ""
        try:
            import pypdf

            reader = pypdf.PdfReader(pdf_path)
            for page in reader.pages:
                txt = page.extract_text()
                if txt:
                    extracted_text += txt + "\n\n"
        except Exception as e:
            logger.warning(f"RAG: Error extrayendo PDF con pypdf: {e}")

        if not extracted_text.strip():
            logger.warning(f"RAG: No se pudo extraer texto del PDF {pdf_path}")
            return 0

        KnowledgeChunk = cls._get_chunk_model()

        KnowledgeChunk.objects.filter(
            source_type="MANUAL_GDS", source_reference_id=str(document.id)
        ).delete()

        chunks = cls.chunk_text(
            f"Manual {document.get_gds_type_display()}: {document.title}\n\n{extracted_text}"
        )
        indexed_count = 0

        for chunk in chunks:
            vector = cls.generate_embedding(chunk, agency=document.agencia)
            KnowledgeChunk.objects.create(
                agencia=document.agencia,
                source_type="MANUAL_GDS",
                source_title=f"{document.title} ({document.get_gds_type_display()})",
                source_reference_id=str(document.id),
                content_chunk=chunk,
                embedding_vector=vector,
            )
            indexed_count += 1

        document.is_indexed = True
        document.indexed_at = timezone.now()
        document.save(update_fields=["is_indexed", "indexed_at"])

        logger.info(f"RAG: Indexado Manual GDS '{document.title}' ({indexed_count} chunks)")
        return indexed_count

    @classmethod
    def index_email_content(
        cls, subject: str, body: str, source_email: str = "", agencia=None
    ) -> int:
        """Indexa un correo informativo del Mailbot en la base RAG."""
        if not body or len(body.strip()) < 50:
            return 0

        KnowledgeChunk = cls._get_chunk_model()

        chunks = cls.chunk_text(f"Comunicado / Correo: {subject}\n\n{body}")
        indexed_count = 0

        for chunk in chunks:
            vector = cls.generate_embedding(chunk, agency=agencia)
            KnowledgeChunk.objects.create(
                agencia=agencia,
                source_type="MAILBOT",
                source_title=subject,
                source_reference_id=source_email,
                content_chunk=chunk,
                embedding_vector=vector,
            )
            indexed_count += 1

        logger.info(f"RAG: Indexado Correo Mailbot '{subject}' ({indexed_count} chunks)")
        return indexed_count

    @classmethod
    def search_relevant_chunks(cls, query: str, agencia=None, limit: int = 4) -> str:
        """
        Realiza una búsqueda semántica RAG sobre los fragmentos de conocimiento indexados.
        Retorna un texto estructurado listo para ser inyectado al contexto del Agente IA.
        """
        if not query or not query.strip():
            return "No se especificó ninguna consulta de búsqueda."

        KnowledgeChunk = cls._get_chunk_model()

        target_agency = agencia or get_current_agency()
        query_vector = cls.generate_embedding(query, agency=target_agency)

        qs = KnowledgeChunk.objects.all()
        if target_agency:
            qs = qs.filter(agencia=target_agency)

        all_chunks = list(qs[:500])
        if not all_chunks:
            return "No hay manuales ni artículos de conocimiento indexados en el sistema."

        scored_chunks = []
        for chunk in all_chunks:
            score = cls.cosine_similarity(query_vector, chunk.embedding_vector or [])
            # También realizar boost si palabras clave de la query aparecen en el texto
            query_words = set(re.findall(r"\w+", query.lower()))
            chunk_words = set(re.findall(r"\w+", chunk.content_chunk.lower()))
            common = query_words.intersection(chunk_words)
            if common:
                score += len(common) * 0.05

            scored_chunks.append((score, chunk))

        # Ordenar por mayor puntaje
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_chunks = scored_chunks[:limit]

        results = []
        for rank, (_score, chunk) in enumerate(top_chunks, 1):
            results.append(
                f"--- FRAGMENTO {rank} (Fuente: {chunk.source_title}) ---\n{chunk.content_chunk}"
            )

        return "\n\n".join(results)

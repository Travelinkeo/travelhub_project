"""Comando de gestión Django para bookings: import_boletos.
"""

import hashlib
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bookings.models import BoletoImportado
from core.models.agencia import Agencia


class Command:
    """Clase Command. Uso: según contexto de la aplicación.
    """
    help = "Importa todos los boletos desde el directorio boletos_importados/"

    def add_arguments(self, parser):
        # add_arguments: Add arguments. Args: según implementación. Returns: según implementación.
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo muestra qué archivos se importarían sin hacerlo",
        )
        parser.add_argument(
            "--agencia-id",
            type=int,
            help="ID de la agencia a la que asignar los boletos (por defecto: primera agencia activa)",
        )
        parser.add_argument(
            "--process",
            action="store_true",
            help="Procesar los boletos después de importarlos (parseo + PDF)",
        )

    def handle(self, *args, **options):
        # handle: Maneja/gestiona . Args: evento/datos. Returns: respuesta.
        dry_run = options["dry_run"]
        agencia_id = options["agencia_id"]
        process_after = options["process"]

        base_path = Path("/app/boletos_importados")
        if not base_path.exists():
            self.stderr.write(f"❌ Directorio no encontrado: {base_path}")
            return

        # Obtener agencia
        if agencia_id:
            try:
                agencia = Agencia.objects.get(id=agencia_id)
            except Agencia.DoesNotExist:
                self.stderr.write(f"❌ Agencia {agencia_id} no existe")
                return
        else:
            agencia = Agencia.objects.filter(activa=True).first()
            if not agencia:
                self.stderr.write("❌ No hay agencias activas")
                return

        self.stdout.write(f"🏢 Usando agencia: {agencia.nombre} (ID: {agencia.id})")

        # Buscar todos los archivos
        archivos = []
        for ext in [".pdf", ".eml", ".txt", ".PDF", ".EML", ".TXT"]:
            archivos.extend(base_path.rglob(f"*{ext}"))

        self.stdout.write(f"📁 Encontrados {len(archivos)} archivos para importar")

        if dry_run:
            for f in archivos:
                size = f.stat().st_size
                self.stdout.write(f"  {f.relative_to(base_path)} ({size:,} bytes)")
            return

        # Importar cada archivo
        imported = 0
        skipped = 0
        errors = 0

        for archivo_path in archivos:
            try:
                relative_path = archivo_path.relative_to(base_path)

                # Calcular hash para evitar duplicados
                with open(archivo_path, "rb") as f:
                    content = f.read()
                    file_hash = hashlib.sha256(content).hexdigest()

                # Verificar si ya existe por hash
                if BoletoImportado.objects.filter(raw_hash=file_hash).exists():
                    self.stdout.write(f"  ⏭️  Saltado (duplicado por hash): {relative_path}")
                    skipped += 1
                    continue

                # Crear el registro
                with open(archivo_path, "rb") as f:
                    django_file = File(f, name=str(relative_path))

                    with transaction.atomic():
                        boleto = BoletoImportado.objects.create(
                            archivo_boleto=django_file,
                            agencia=agencia,
                            estado_parseo=BoletoImportado.EstadoParseo.PENDIENTE,
                            raw_hash=file_hash,
                        )

                self.stdout.write(
                    f"  ✅ Importado: {relative_path} (ID: {boleto.id_boleto_importado})"
                )
                imported += 1

            except Exception as e:
                self.stderr.write(f"  ❌ Error importando {archivo_path}: {e}")
                errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n📊 Resumen: {imported} importados, {skipped} duplicados saltados, {errors} errores"
            )
        )

        # Procesar boletos si se solicita
        if process_after and imported > 0:
            self.stdout.write("\n🔄 Procesando boletos importados...")
            from apps.automation.services.ticket_parser_service import TicketParserService

            parser = TicketParserService()
            boletos = BoletoImportado.objects.filter(
                agencia=agencia, estado_parseo=BoletoImportado.EstadoParseo.PENDIENTE
            )

            for boleto in boletos:
                try:
                    self.stdout.write(f"  Procesando boleto {boleto.id_boleto_importado}...")
                    parser.procesar_boleto(
                        boleto_id=boleto.id_boleto_importado, bypass_cache=True, ignore_manual=True
                    )
                    self.stdout.write(f"  ✅ Boleto {boleto.id_boleto_importado} procesado")
                except Exception as e:
                    self.stderr.write(
                        f"  ❌ Error procesando boleto {boleto.id_boleto_importado}: {e}"
                    )

            self.stdout.write(self.style.SUCCESS("✅ Procesamiento completado"))

import logging

from django.core.management.base import BaseCommand

from apps.automation.services.rag_historical_ingestion import RAGHistoricalEmailIngestionService
from core.models import Agencia

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ingesta y vectoriza masivamente correos históricos (ej. travelinkeo@gmail.com) para el RAG Knowledge Base."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            default="travelinkeo@gmail.com",
            help="Dirección de correo a consultar (default: travelinkeo@gmail.com)",
        )
        parser.add_argument(
            "--password",
            type=str,
            required=True,
            help="Contraseña de Aplicación de Google (App Password) de la cuenta de correo",
        )
        parser.add_argument(
            "--since-year",
            type=int,
            default=2013,
            help="Año inicial de búsqueda en IMAP (default: 2013)",
        )
        parser.add_argument(
            "--until-year",
            type=int,
            default=None,
            help="Año final de búsqueda opcional",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Número máximo de correos a procesar en esta ejecución (default: 100)",
        )
        parser.add_argument(
            "--agencia-id",
            type=int,
            default=2,
            help="ID de la agencia a asociar los datos (default: 2 - Travelinkeo)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Modo simulación: Muestra qué correos procesaría sin guardar vectores",
        )

    def handle(self, *args, **options):
        email_user = options["email"]
        email_pass = options["password"]
        since_year = options["since_year"]
        until_year = options["until_year"]
        limit = options["limit"]
        agencia_id = options["agencia_id"]
        dry_run = options["dry_run"]

        self.stdout.write(
            self.style.SUCCESS(
                f"🚀 Iniciando Ingesta Histórica RAG para {email_user} (Desde año {since_year})..."
            )
        )

        try:
            agencia = Agencia.objects.get(id=agencia_id)
        except Agencia.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ La agencia con ID {agencia_id} no existe."))
            return

        stats = RAGHistoricalEmailIngestionService.ingest_from_imap(
            agencia=agencia,
            email_user=email_user,
            email_pass=email_pass,
            since_year=since_year,
            until_year=until_year,
            limit=limit,
            dry_run=dry_run,
        )

        self.stdout.write(self.style.SUCCESS("\n📊 RESUMEN DE PROCESAMIENTO RAG:"))
        self.stdout.write(f" - Correos encontrados en IMAP: {stats['total_found']}")
        self.stdout.write(f" - Correos procesados e indexados: {stats['processed']}")
        self.stdout.write(f" - Chunks vectoriales creados: {stats['chunks_created']}")
        self.stdout.write(f" - Correos ya existentes omitidos: {stats['skipped_existing']}")
        self.stdout.write(f" - Correos omitidos (ruido/no informativos): {stats['skipped_noise']}")
        self.stdout.write(f" - Errores encontrados: {stats['errors']}")

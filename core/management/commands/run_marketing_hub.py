from django.core.management.base import BaseCommand

from apps.automation.services.marketing_intelligence_service import MarketingIntelligenceService


class Command(BaseCommand):
    """Command."""

    help = "Ejecuta el motor de Marketing Intelligence para generar contenido automático basado en tendencias de reserva."

    def add_arguments(self, parser):
        """add_arguments."""
        parser.add_argument(
            "--agency-id",
            type=int,
            help="ID de la agencia específica a procesar (opcional).",
        )

    def handle(self, *args, **options):
        """handle."""
        agency_id = options["agency_id"]
        self.stdout.write(self.style.NOTICE("Iniciando Marketing Intelligence Hub..."))

        results = MarketingIntelligenceService.run_automated_marketing_engine(agency_id=agency_id)

        if not results:
            self.stdout.write(
                self.style.WARNING("No se generaron nuevas campañas (sin tendencias detectadas).")
            )
        else:
            for res in results:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Campaña creada para {res['agencia']}: {res['trend']} (ID: {res['campaign_id']})"
                    )
                )

        self.stdout.write(self.style.SUCCESS("Proceso completado."))

from django.core.management.base import BaseCommand

from apps.reports.tasks import enviar_reportes_programados_task


class Command(BaseCommand):
    help = "Ejecuta el envío de reportes KPI programados que estén pendientes"

    def handle(self, *args, **options):
        self.stdout.write("Enviando reportes programados...")
        result = enviar_reportes_programados_task()
        self.stdout.write(self.style.SUCCESS(f"Reportes enviados: {result}"))

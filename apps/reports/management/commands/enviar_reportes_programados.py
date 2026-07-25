"""Comando de gestión Django para reports: enviar_reportes_programados.
"""

from django.core.management.base import BaseCommand

from apps.reports.tasks import enviar_reportes_programados_task


class Command:
    """Clase Command. Uso: según contexto de la aplicación.
    """
    help = "Ejecuta el envío de reportes KPI programados que estén pendientes"

    def handle(self, *args, **options):
        # handle: Maneja/gestiona . Args: evento/datos. Returns: respuesta.
        self.stdout.write("Enviando reportes programados...")
        result = enviar_reportes_programados_task()
        self.stdout.write(self.style.SUCCESS(f"Reportes enviados: {result}"))

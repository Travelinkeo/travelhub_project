"""
Comando para ejecutar conciliación de reportes de proveedores.
Usa el servicio unificado SmartReconciliationService.
"""

from django.core.management.base import BaseCommand

from apps.finance.models_stubs import ReporteReconciliacion
from apps.finance.services.smart_reconciliation_service import SmartReconciliationService


class Command(BaseCommand):
    help = "Procesa un reporte de reconciliación usando IA y cruce determinístico"

    def add_arguments(self, parser):
        parser.add_argument(
            "reporte_id", type=str, help="UUID del ReporteReconciliacion a procesar"
        )

    def handle(self, *args, **options):
        reporte_id = options["reporte_id"]
        self.stdout.write(
            self.style.SUCCESS(f"Iniciando procesamiento del reporte {reporte_id}...")
        )

        try:
            SmartReconciliationService.procesar_reporte(reporte_id)

            reporte = ReporteReconciliacion.objects.get(pk=reporte_id)
            self.stdout.write(self.style.SUCCESS("Procesamiento finalizado."))
            self.stdout.write(f"Estado: {reporte.estado}")
            resumen = reporte.resumen_conciliacion or {}
            self.stdout.write(f"Total líneas: {resumen.get('total_lineas', 'N/A')}")
            self.stdout.write(
                self.style.WARNING(f"Discrepancias: {resumen.get('discrepancias', 0)}")
            )
            self.stdout.write(
                self.style.WARNING(f"Huérfanos reporte: {resumen.get('huerfanos_reporte', 0)}")
            )
            self.stdout.write(
                self.style.WARNING(f"Huérfanos local: {resumen.get('huerfanos_local', 0)}")
            )
        except ReporteReconciliacion.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Reporte con ID {reporte_id} no encontrado."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error procesando reporte: {str(e)}"))
            raise

from django.core.management.base import BaseCommand
from apps.finance.models import ReporteProveedor
from apps.finance.services.reconciliation_service import ReconciliationService

class Command(BaseCommand):
    help = 'Procesa un reporte de proveedor para reconciliación'

    def add_arguments(self, parser):
        parser.add_argument('reporte_id', type=int, help='ID del ReporteProveedor a procesar')

    def handle(self, *args, **options):
        reporte_id = options['reporte_id']
        self.stdout.write(self.style.SUCCESS(f'Iniciando procesamiento del reporte {reporte_id}...'))
        
        ReconciliationService.process_report(reporte_id)
        
        reporte = ReporteProveedor.objects.get(pk=reporte_id)
        self.stdout.write(self.style.SUCCESS(f'Procesamiento finalizado.'))
        self.stdout.write(f'Total registros: {reporte.total_registros}')
        self.stdout.write(self.style.WARNING(f'Diferencias encontradas: {reporte.total_con_diferencia}'))

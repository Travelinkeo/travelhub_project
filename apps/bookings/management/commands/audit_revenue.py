from django.core.management.base import BaseCommand
from apps.bookings.services.revenue_auditor import RevenueAuditorService
from django.utils import timezone
import json

class Command(BaseCommand):
    help = 'Ejecuta el Revenue Leak AI para detectar fugas de dinero en las últimas ventas.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Días a auditar (Default: 30)')
        parser.add_argument('--json', action='store_true', help='Salida en formato JSON')

    def handle(self, *args, **options):
        days = options['days']
        auditor = RevenueAuditorService()
        
        self.stdout.write(self.style.SUCCESS(f"🚀 Iniciando Revenue Leak AI (Escáner de {days} días)..."))
        
        report = auditor.run_full_audit(days=days)
        
        if options['json']:
            self.stdout.write(json.dumps(report, indent=4))
            return

        # Resumen en Tabla (Manual formatting for CLI)
        self.stdout.write("-" * 50)
        self.stdout.write(f"Total Ventas Analizadas: {report['total_ventas_auditadas']}")
        self.stdout.write(f"Ventas con Hallazgos:    {report['ventas_con_fugas']}")
        self.stdout.write(f"Hallazgos Críticos:      {report['hallazgos_criticos']}")
        self.stdout.write("-" * 50)

        if report['detalles']:
            self.stdout.write(self.style.WARNING("\nDETALLES DE FUGA DETECTADOS:"))
            for item in report['detalles']:
                self.stdout.write(f"📍 PNR: {item['localizador']} (ID:{item['venta_id']})")
                for f in item['findings']:
                    color = self.style.ERROR if f['severity'] == 'HIGH' else self.style.WARNING
                    self.stdout.write(color(f"   - [{f['type']}] {f['message']}"))
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ ¡Felicitaciones! No se detectaron fugas financieras en este periodo."))

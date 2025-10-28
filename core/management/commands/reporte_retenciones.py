# core/management/commands/reporte_retenciones.py
"""Comando para generar reporte de retenciones ISLR"""
from datetime import datetime
from django.core.management.base import BaseCommand
from core.services.reporte_retenciones import ReporteRetencionesService


class Command(BaseCommand):
    help = 'Genera reporte de Retenciones ISLR para un período'
    
    def add_arguments(self, parser):
        parser.add_argument('--mes', type=int, help='Mes (1-12)')
        parser.add_argument('--anio', type=int, help='Año (YYYY)')
        parser.add_argument('--fecha-inicio', type=str, help='Fecha inicio (YYYY-MM-DD)')
        parser.add_argument('--fecha-fin', type=str, help='Fecha fin (YYYY-MM-DD)')
        parser.add_argument('--estado', type=str, choices=['PEN', 'APL', 'ANU'],
                          help='Filtrar por estado')
        parser.add_argument('--formato', type=str, default='consola',
                          choices=['consola', 'csv'], help='Formato de salida')
        parser.add_argument('--archivo', type=str, help='Nombre del archivo CSV')
    
    def handle(self, *args, **options):
        # Determinar período
        if options['mes'] and options['anio']:
            from calendar import monthrange
            mes, anio = options['mes'], options['anio']
            fecha_inicio = datetime(anio, mes, 1).date()
            ultimo_dia = monthrange(anio, mes)[1]
            fecha_fin = datetime(anio, mes, ultimo_dia).date()
        elif options['fecha_inicio'] and options['fecha_fin']:
            fecha_inicio = datetime.strptime(options['fecha_inicio'], '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(options['fecha_fin'], '%Y-%m-%d').date()
        else:
            self.stdout.write(self.style.ERROR(
                'Debe especificar --mes y --anio, o --fecha-inicio y --fecha-fin'
            ))
            return
        
        self.stdout.write(f'Generando reporte de retenciones del {fecha_inicio} al {fecha_fin}...')
        
        # Generar reporte
        reporte = ReporteRetencionesService.reporte_periodo(
            fecha_inicio, fecha_fin, options.get('estado')
        )
        
        if options['formato'] == 'csv':
            csv_content = ReporteRetencionesService.exportar_csv(reporte)
            archivo = options['archivo'] or f'retenciones_islr_{fecha_inicio}_{fecha_fin}.csv'
            
            with open(archivo, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            
            self.stdout.write(self.style.SUCCESS(f'Archivo CSV generado: {archivo}'))
        else:
            # Mostrar en consola
            self.stdout.write('\n' + '='*80)
            self.stdout.write(self.style.SUCCESS('REPORTE DE RETENCIONES ISLR'))
            self.stdout.write(f'Período: {fecha_inicio} al {fecha_fin}')
            self.stdout.write('='*80 + '\n')
            
            # Por tipo de operación
            if reporte['por_tipo_operacion']:
                self.stdout.write(self.style.WARNING('POR TIPO DE OPERACIÓN:'))
                for tipo, datos in reporte['por_tipo_operacion'].items():
                    self.stdout.write(f"\n{tipo}:")
                    self.stdout.write(f"  Cantidad: {datos['cantidad']}")
                    self.stdout.write(f"  Base Imponible: ${datos['base_imponible']:,.2f}")
                    self.stdout.write(f"  Monto Retenido: ${datos['monto_retenido']:,.2f}")
            
            # Detalle
            self.stdout.write('\n' + self.style.WARNING('DETALLE:'))
            for item in reporte['detalle']:
                self.stdout.write(
                    f"{item['fecha_emision']} | {item['numero_comprobante']:15} | "
                    f"{item['cliente'][:30]:30} | Base: ${item['base_imponible']:>10.2f} | "
                    f"Ret: ${item['monto_retenido']:>8.2f} | {item['estado']}"
                )
            
            # Totales
            self.stdout.write('\n' + '='*80)
            self.stdout.write(self.style.SUCCESS('TOTALES:'))
            self.stdout.write(f"Total Retenciones: {reporte['totales']['cantidad']}")
            self.stdout.write(f"Base Imponible Total: ${reporte['totales']['base_imponible']:,.2f}")
            self.stdout.write(f"Monto Retenido Total: ${reporte['totales']['monto_retenido']:,.2f}")
            self.stdout.write('='*80 + '\n')

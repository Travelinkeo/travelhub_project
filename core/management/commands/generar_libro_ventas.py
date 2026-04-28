# core/management/commands/generar_libro_ventas.py
"""
Comando para generar Libro de Ventas desde la terminal
"""
from datetime import datetime
from django.core.management.base import BaseCommand
from core.services.libro_ventas import LibroVentasService


class Command(BaseCommand):
    help = 'Genera el Libro de Ventas para un período específico'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--mes',
            type=int,
            help='Mes (1-12)',
        )
        parser.add_argument(
            '--anio',
            type=int,
            help='Año (YYYY)',
        )
        parser.add_argument(
            '--fecha-inicio',
            type=str,
            help='Fecha inicio (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--fecha-fin',
            type=str,
            help='Fecha fin (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--formato',
            type=str,
            default='consola',
            choices=['consola', 'csv'],
            help='Formato de salida (consola o csv)',
        )
        parser.add_argument(
            '--archivo',
            type=str,
            help='Nombre del archivo CSV (solo si formato=csv)',
        )
    
    def handle(self, *args, **options):
        # Determinar período
        if options['mes'] and options['anio']:
            mes = options['mes']
            anio = options['anio']
            
            from calendar import monthrange
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
        
        self.stdout.write(f'Generando Libro de Ventas del {fecha_inicio} al {fecha_fin}...')
        
        # Generar libro de ventas
        libro_ventas = LibroVentasService.generar_libro_ventas(fecha_inicio, fecha_fin)
        
        if options['formato'] == 'csv':
            # Exportar a CSV
            csv_content = LibroVentasService.exportar_csv(libro_ventas)
            
            archivo = options['archivo'] or f'libro_ventas_{fecha_inicio}_{fecha_fin}.csv'
            
            with open(archivo, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            
            self.stdout.write(self.style.SUCCESS(f'Archivo CSV generado: {archivo}'))
        
        else:
            # Mostrar en consola
            self.stdout.write('\n' + '='*80)
            self.stdout.write(self.style.SUCCESS('LIBRO DE VENTAS'))
            self.stdout.write(f'Período: {fecha_inicio} al {fecha_fin}')
            self.stdout.write('='*80 + '\n')
            
            # Ventas propias
            self.stdout.write(self.style.WARNING('VENTAS PROPIAS:'))
            for venta in libro_ventas['ventas_propias']:
                self.stdout.write(
                    f"{venta['fecha']} | {venta['numero_factura']} | "
                    f"{venta['cliente_nombre'][:30]:30} | "
                    f"Base: ${venta['base_gravada']:>10.2f} | "
                    f"IVA: ${venta['iva_16']:>8.2f} | "
                    f"Total: ${venta['total']:>10.2f}"
                )
            
            # Ventas por cuenta de terceros
            if libro_ventas['ventas_terceros']:
                self.stdout.write('\n' + self.style.WARNING('VENTAS POR CUENTA DE TERCEROS:'))
                for venta in libro_ventas['ventas_terceros']:
                    self.stdout.write(
                        f"{venta['fecha']} | {venta['numero_factura']} | "
                        f"{venta['cliente_nombre'][:30]:30} | "
                        f"Tercero: {venta.get('tercero_nombre', 'N/A')[:20]:20} | "
                        f"Total: ${venta['total']:>10.2f}"
                    )
            
            # Totales
            self.stdout.write('\n' + '='*80)
            self.stdout.write(self.style.SUCCESS('TOTALES:'))
            self.stdout.write(f"Total Facturas: {libro_ventas['resumen']['total_facturas']}")
            self.stdout.write(f"  - Ventas Propias: {libro_ventas['resumen']['facturas_propias']}")
            self.stdout.write(f"  - Ventas Terceros: {libro_ventas['resumen']['facturas_terceros']}")
            
            self.stdout.write('\nVENTAS PROPIAS:')
            self.stdout.write(f"  Base Gravada:    ${libro_ventas['totales']['propias']['base_gravada']:>12.2f}")
            self.stdout.write(f"  Base Exenta:     ${libro_ventas['totales']['propias']['base_exenta']:>12.2f}")
            self.stdout.write(f"  Base Exportación:${libro_ventas['totales']['propias']['base_exportacion']:>12.2f}")
            self.stdout.write(f"  IVA 16%:         ${libro_ventas['totales']['propias']['iva_16']:>12.2f}")
            self.stdout.write(f"  IVA Adicional:   ${libro_ventas['totales']['propias']['iva_adicional']:>12.2f}")
            self.stdout.write(f"  IGTF:            ${libro_ventas['totales']['propias']['igtf']:>12.2f}")
            self.stdout.write(f"  Total:           ${libro_ventas['totales']['propias']['total']:>12.2f}")
            
            if libro_ventas['ventas_terceros']:
                self.stdout.write('\nVENTAS TERCEROS:')
                self.stdout.write(f"  Base Exenta:     ${libro_ventas['totales']['terceros']['base_exenta']:>12.2f}")
                self.stdout.write(f"  Total:           ${libro_ventas['totales']['terceros']['total']:>12.2f}")
            
            self.stdout.write('\n' + self.style.SUCCESS('DÉBITO FISCAL TOTAL (IVA A DECLARAR):'))
            self.stdout.write(f"  ${libro_ventas['resumen']['debito_fiscal']:>12.2f}")
            self.stdout.write('='*80 + '\n')

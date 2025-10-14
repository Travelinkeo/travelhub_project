# contabilidad/management/commands/generar_reporte.py
"""
Comando para generar reportes contables desde la línea de comandos.

Uso:
    python manage.py generar_reporte balance_comprobacion --desde 2025-01-01 --hasta 2025-01-31
    python manage.py generar_reporte estado_resultados --desde 2025-01-01 --hasta 2025-01-31
    python manage.py generar_reporte balance_general --fecha 2025-01-31
    python manage.py generar_reporte libro_diario --desde 2025-01-01 --hasta 2025-01-31
"""

from datetime import date
from django.core.management.base import BaseCommand, CommandError
from contabilidad.reportes import ReportesContables


class Command(BaseCommand):
    help = 'Genera reportes contables'

    def add_arguments(self, parser):
        parser.add_argument(
            'tipo',
            type=str,
            choices=['balance_comprobacion', 'estado_resultados', 'balance_general', 'libro_diario'],
            help='Tipo de reporte a generar'
        )
        parser.add_argument('--desde', type=str, help='Fecha desde (YYYY-MM-DD)')
        parser.add_argument('--hasta', type=str, help='Fecha hasta (YYYY-MM-DD)')
        parser.add_argument('--fecha', type=str, help='Fecha de corte (YYYY-MM-DD)')
        parser.add_argument('--moneda', type=str, default='USD', choices=['USD', 'BSD'])

    def handle(self, *args, **options):
        tipo = options['tipo']
        moneda = options['moneda']
        
        try:
            if tipo == 'balance_general':
                if not options['fecha']:
                    raise CommandError('--fecha es requerido para balance_general')
                
                fecha_corte = date.fromisoformat(options['fecha'])
                resultado = ReportesContables.balance_general(fecha_corte, moneda)
                
                self.stdout.write(self.style.SUCCESS(f"\n=== BALANCE GENERAL al {fecha_corte} ({moneda}) ===\n"))
                self.stdout.write(f"Activos:    {resultado['activos']:>15,.2f}")
                self.stdout.write(f"Pasivos:    {resultado['pasivos']:>15,.2f}")
                self.stdout.write(f"Patrimonio: {resultado['patrimonio']:>15,.2f}")
                self.stdout.write(f"{'='*40}")
                self.stdout.write(f"Total P+P:  {resultado['total_pasivo_patrimonio']:>15,.2f}")
                
                if resultado['cuadrado']:
                    self.stdout.write(self.style.SUCCESS("\n[OK] Balance cuadrado"))
                else:
                    self.stdout.write(self.style.ERROR("\n[ERROR] Balance descuadrado"))
            
            else:
                if not options['desde'] or not options['hasta']:
                    raise CommandError('--desde y --hasta son requeridos')
                
                fecha_desde = date.fromisoformat(options['desde'])
                fecha_hasta = date.fromisoformat(options['hasta'])
                
                if tipo == 'balance_comprobacion':
                    resultado = ReportesContables.balance_comprobacion(fecha_desde, fecha_hasta, moneda)
                    
                    self.stdout.write(self.style.SUCCESS(
                        f"\n=== BALANCE DE COMPROBACIÓN {fecha_desde} a {fecha_hasta} ({moneda}) ===\n"
                    ))
                    self.stdout.write(f"{'Código':<12} {'Cuenta':<40} {'Debe':>15} {'Haber':>15} {'Saldo':>15}")
                    self.stdout.write("="*100)
                    
                    for cuenta in resultado['cuentas']:
                        self.stdout.write(
                            f"{cuenta['codigo']:<12} {cuenta['nombre']:<40} "
                            f"{cuenta['debe']:>15,.2f} {cuenta['haber']:>15,.2f} {cuenta['saldo']:>15,.2f}"
                        )
                    
                    self.stdout.write("="*100)
                    self.stdout.write(
                        f"{'TOTALES':<52} "
                        f"{resultado['totales']['debe']:>15,.2f} {resultado['totales']['haber']:>15,.2f}"
                    )
                
                elif tipo == 'estado_resultados':
                    resultado = ReportesContables.estado_resultados(fecha_desde, fecha_hasta, moneda)
                    
                    self.stdout.write(self.style.SUCCESS(
                        f"\n=== ESTADO DE RESULTADOS {fecha_desde} a {fecha_hasta} ({moneda}) ===\n"
                    ))
                    self.stdout.write(f"Ingresos:      {resultado['ingresos']:>15,.2f}")
                    self.stdout.write(f"Gastos:        {resultado['gastos']:>15,.2f}")
                    self.stdout.write(f"{'='*40}")
                    
                    utilidad = resultado['utilidad_neta']
                    if utilidad >= 0:
                        self.stdout.write(self.style.SUCCESS(f"Utilidad Neta: {utilidad:>15,.2f}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"Pérdida Neta:  {abs(utilidad):>15,.2f}"))
                
                elif tipo == 'libro_diario':
                    asientos = ReportesContables.libro_diario(fecha_desde, fecha_hasta, moneda)
                    
                    self.stdout.write(self.style.SUCCESS(
                        f"\n=== LIBRO DIARIO {fecha_desde} a {fecha_hasta} ({moneda}) ===\n"
                    ))
                    
                    for asiento in asientos:
                        self.stdout.write(f"\nAsiento: {asiento['numero']} | Fecha: {asiento['fecha']} | {asiento['tipo']}")
                        self.stdout.write(f"Descripción: {asiento['descripcion']}")
                        self.stdout.write("-" * 80)
                        
                        for detalle in asiento['detalles']:
                            if detalle['debe'] > 0:
                                self.stdout.write(
                                    f"  {detalle['cuenta_codigo']} {detalle['cuenta_nombre']:<40} "
                                    f"{detalle['debe']:>12,.2f}"
                                )
                            else:
                                self.stdout.write(
                                    f"      {detalle['cuenta_codigo']} {detalle['cuenta_nombre']:<36} "
                                    f"{detalle['haber']:>12,.2f}"
                                )
                        
                        self.stdout.write(f"{'Total:':<50} {asiento['total_debe']:>12,.2f} = {asiento['total_haber']:>12,.2f}")
        
        except ValueError as e:
            raise CommandError(f'Error en formato de fecha: {e}')
        except Exception as e:
            raise CommandError(f'Error generando reporte: {e}')

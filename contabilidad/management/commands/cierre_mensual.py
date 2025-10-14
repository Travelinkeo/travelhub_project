# contabilidad/management/commands/cierre_mensual.py
"""
Comando para ejecutar el cierre contable mensual automatizado.

Uso:
    python manage.py cierre_mensual --mes 1 --anio 2025
    python manage.py cierre_mensual  # Mes anterior
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from contabilidad.models import AsientoContable, DetalleAsiento, PlanContable
from contabilidad.services import ContabilidadService
from contabilidad.reportes import ReportesContables

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Ejecuta el cierre contable mensual automatizado'

    def add_arguments(self, parser):
        parser.add_argument('--mes', type=int, help='Mes a cerrar (1-12)')
        parser.add_argument('--anio', type=int, help='Año a cerrar')
        parser.add_argument('--dry-run', action='store_true', help='Simula sin guardar')

    def handle(self, *args, **options):
        # Determinar período
        if options['mes'] and options['anio']:
            mes = options['mes']
            anio = options['anio']
        else:
            # Mes anterior por defecto
            hoy = date.today()
            primer_dia_mes = hoy.replace(day=1)
            ultimo_dia_mes_anterior = primer_dia_mes - timedelta(days=1)
            mes = ultimo_dia_mes_anterior.month
            anio = ultimo_dia_mes_anterior.year
        
        if not (1 <= mes <= 12):
            raise CommandError('Mes debe estar entre 1 y 12')
        
        dry_run = options['dry_run']
        
        self.stdout.write(f'\n=== CIERRE CONTABLE {mes:02d}/{anio} ===\n')
        
        try:
            # 1. Provisionar INATUR
            self.stdout.write('1. Provisionando INATUR 1%...')
            if not dry_run:
                ContabilidadService.provisionar_contribucion_inatur(mes, anio)
            self.stdout.write(self.style.SUCCESS('   [OK]'))
            
            # 2. Verificar balance
            self.stdout.write('2. Verificando balance...')
            ultimo_dia = self._ultimo_dia_mes(mes, anio)
            balance = ReportesContables.balance_general(ultimo_dia, 'USD')
            
            if balance['cuadrado']:
                self.stdout.write(self.style.SUCCESS('   [OK] Balance cuadrado'))
            else:
                self.stdout.write(self.style.ERROR('   [ERROR] Balance descuadrado'))
                diff = balance['activos'] - balance['total_pasivo_patrimonio']
                self.stdout.write(f'   Diferencia: {diff}')
            
            # 3. Cerrar resultado del período
            self.stdout.write('3. Cerrando resultado del período...')
            if not dry_run:
                self._cerrar_resultado(mes, anio)
            self.stdout.write(self.style.SUCCESS('   [OK]'))
            
            # 4. Resumen
            self.stdout.write('\n=== RESUMEN ===')
            resultado = ReportesContables.estado_resultados(
                date(anio, mes, 1),
                ultimo_dia,
                'USD'
            )
            
            self.stdout.write(f'Ingresos:  {resultado["ingresos"]:>12,.2f} USD')
            self.stdout.write(f'Gastos:    {resultado["gastos"]:>12,.2f} USD')
            
            utilidad = resultado['utilidad_neta']
            if utilidad >= 0:
                self.stdout.write(self.style.SUCCESS(f'Utilidad:  {utilidad:>12,.2f} USD'))
            else:
                self.stdout.write(self.style.ERROR(f'Pérdida:   {abs(utilidad):>12,.2f} USD'))
            
            if dry_run:
                self.stdout.write(self.style.WARNING('\n[DRY-RUN] No se guardaron cambios'))
            else:
                self.stdout.write(self.style.SUCCESS('\n[OK] Cierre completado'))
        
        except Exception as e:
            logger.error(f"Error en cierre mensual: {e}")
            raise CommandError(f'Error: {e}')
    
    def _ultimo_dia_mes(self, mes, anio):
        """Obtiene el último día del mes"""
        if mes == 12:
            return date(anio, 12, 31)
        else:
            return date(anio, mes + 1, 1) - timedelta(days=1)
    
    @transaction.atomic
    def _cerrar_resultado(self, mes, anio):
        """
        Cierra el resultado del período trasladando utilidad/pérdida a patrimonio.
        Genera asiento de cierre.
        """
        primer_dia = date(anio, mes, 1)
        ultimo_dia = self._ultimo_dia_mes(mes, anio)
        
        # Calcular resultado
        resultado = ReportesContables.estado_resultados(primer_dia, ultimo_dia, 'USD')
        utilidad = resultado['utilidad_neta']
        
        if abs(utilidad) < Decimal('0.01'):
            logger.info("No hay utilidad/pérdida a cerrar")
            return
        
        # Crear asiento de cierre
        asiento = AsientoContable.objects.create(
            fecha_contable=ultimo_dia,
            descripcion_general=f"Cierre resultado {mes:02d}/{anio}",
            tipo_asiento=AsientoContable.TipoAsiento.CIERRE,
            referencia_documento=f"CIERRE-{anio}{mes:02d}",
            estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
            tasa_cambio_aplicada=Decimal('1.00'),
            moneda=None
        )
        
        # Obtener cuenta de resultados acumulados
        cuenta_resultados = PlanContable.objects.filter(
            codigo_cuenta__startswith='3.2'  # Resultados Acumulados
        ).first()
        
        if not cuenta_resultados:
            raise Exception("No existe cuenta de Resultados Acumulados (3.2)")
        
        if utilidad > 0:
            # Utilidad: Débito Ingresos, Crédito Resultados
            # Simplificado: solo trasladar neto
            DetalleAsiento.objects.create(
                asiento=asiento,
                linea=1,
                cuenta_contable=cuenta_resultados,
                debe=Decimal('0.00'),
                haber=utilidad,
                debe_bsd=Decimal('0.00'),
                haber_bsd=Decimal('0.00'),
                descripcion_linea=f"Utilidad del período {mes:02d}/{anio}"
            )
        else:
            # Pérdida: Débito Resultados, Crédito Gastos
            DetalleAsiento.objects.create(
                asiento=asiento,
                linea=1,
                cuenta_contable=cuenta_resultados,
                debe=abs(utilidad),
                haber=Decimal('0.00'),
                debe_bsd=Decimal('0.00'),
                haber_bsd=Decimal('0.00'),
                descripcion_linea=f"Pérdida del período {mes:02d}/{anio}"
            )
        
        asiento.calcular_totales()
        logger.info(f"Asiento de cierre {asiento.numero_asiento} generado")

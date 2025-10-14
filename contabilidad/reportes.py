# contabilidad/reportes.py
"""
Generación de reportes contables según VEN-NIF.
Balance de Comprobación, Estado de Resultados, Balance General, Libro Diario/Mayor.
"""

from decimal import Decimal
from datetime import date
from typing import Dict, List, Optional
from django.db.models import Sum, Q
from django.utils.translation import gettext_lazy as _

from .models import PlanContable, AsientoContable, DetalleAsiento


class ReportesContables:
    """Generador de reportes contables"""
    
    @staticmethod
    def balance_comprobacion(
        fecha_desde: date,
        fecha_hasta: date,
        moneda: str = 'USD'
    ) -> Dict:
        """
        Balance de Comprobación para un período.
        
        Args:
            fecha_desde: Fecha inicial
            fecha_hasta: Fecha final
            moneda: 'USD' o 'BSD'
            
        Returns:
            Dict con cuentas y sus saldos
        """
        campo_debe = 'debe_bsd' if moneda == 'BSD' else 'debe'
        campo_haber = 'haber_bsd' if moneda == 'BSD' else 'haber'
        
        cuentas = PlanContable.objects.filter(permite_movimientos=True).order_by('codigo_cuenta')
        
        resultado = {
            'periodo': {'desde': fecha_desde, 'hasta': fecha_hasta},
            'moneda': moneda,
            'cuentas': [],
            'totales': {'debe': Decimal('0'), 'haber': Decimal('0')}
        }
        
        for cuenta in cuentas:
            movimientos = DetalleAsiento.objects.filter(
                cuenta_contable=cuenta,
                asiento__fecha_contable__range=(fecha_desde, fecha_hasta),
                asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO
            ).aggregate(
                total_debe=Sum(campo_debe),
                total_haber=Sum(campo_haber)
            )
            
            debe = movimientos['total_debe'] or Decimal('0')
            haber = movimientos['total_haber'] or Decimal('0')
            saldo = debe - haber
            
            if debe != 0 or haber != 0:
                resultado['cuentas'].append({
                    'codigo': cuenta.codigo_cuenta,
                    'nombre': cuenta.nombre_cuenta,
                    'debe': debe,
                    'haber': haber,
                    'saldo': saldo,
                    'naturaleza': cuenta.naturaleza
                })
                
                resultado['totales']['debe'] += debe
                resultado['totales']['haber'] += haber
        
        return resultado
    
    @staticmethod
    def estado_resultados(
        fecha_desde: date,
        fecha_hasta: date,
        moneda: str = 'USD'
    ) -> Dict:
        """
        Estado de Resultados (P&L) para un período.
        
        Returns:
            Dict con ingresos, costos, gastos y utilidad
        """
        campo_debe = 'debe_bsd' if moneda == 'BSD' else 'debe'
        campo_haber = 'haber_bsd' if moneda == 'BSD' else 'haber'
        
        # Ingresos (naturaleza acreedora)
        ingresos = DetalleAsiento.objects.filter(
            cuenta_contable__tipo_cuenta=PlanContable.TipoCuentaChoices.INGRESO,
            asiento__fecha_contable__range=(fecha_desde, fecha_hasta),
            asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO
        ).aggregate(
            total=Sum(campo_haber)
        )['total'] or Decimal('0')
        
        # Gastos (naturaleza deudora)
        gastos = DetalleAsiento.objects.filter(
            cuenta_contable__tipo_cuenta=PlanContable.TipoCuentaChoices.GASTO,
            asiento__fecha_contable__range=(fecha_desde, fecha_hasta),
            asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO
        ).aggregate(
            total=Sum(campo_debe)
        )['total'] or Decimal('0')
        
        utilidad = ingresos - gastos
        
        return {
            'periodo': {'desde': fecha_desde, 'hasta': fecha_hasta},
            'moneda': moneda,
            'ingresos': ingresos,
            'gastos': gastos,
            'utilidad_neta': utilidad
        }
    
    @staticmethod
    def balance_general(fecha_corte: date, moneda: str = 'USD') -> Dict:
        """
        Balance General (Estado de Situación Financiera) a una fecha.
        
        Returns:
            Dict con activos, pasivos y patrimonio
        """
        campo_debe = 'debe_bsd' if moneda == 'BSD' else 'debe'
        campo_haber = 'haber_bsd' if moneda == 'BSD' else 'haber'
        
        # Activos (saldo deudor)
        activos = DetalleAsiento.objects.filter(
            cuenta_contable__tipo_cuenta=PlanContable.TipoCuentaChoices.ACTIVO,
            asiento__fecha_contable__lte=fecha_corte,
            asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO
        ).aggregate(
            debe=Sum(campo_debe),
            haber=Sum(campo_haber)
        )
        total_activos = (activos['debe'] or Decimal('0')) - (activos['haber'] or Decimal('0'))
        
        # Pasivos (saldo acreedor)
        pasivos = DetalleAsiento.objects.filter(
            cuenta_contable__tipo_cuenta=PlanContable.TipoCuentaChoices.PASIVO,
            asiento__fecha_contable__lte=fecha_corte,
            asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO
        ).aggregate(
            debe=Sum(campo_debe),
            haber=Sum(campo_haber)
        )
        total_pasivos = (pasivos['haber'] or Decimal('0')) - (pasivos['debe'] or Decimal('0'))
        
        # Patrimonio (saldo acreedor)
        patrimonio = DetalleAsiento.objects.filter(
            cuenta_contable__tipo_cuenta=PlanContable.TipoCuentaChoices.PATRIMONIO,
            asiento__fecha_contable__lte=fecha_corte,
            asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO
        ).aggregate(
            debe=Sum(campo_debe),
            haber=Sum(campo_haber)
        )
        total_patrimonio = (patrimonio['haber'] or Decimal('0')) - (patrimonio['debe'] or Decimal('0'))
        
        return {
            'fecha_corte': fecha_corte,
            'moneda': moneda,
            'activos': total_activos,
            'pasivos': total_pasivos,
            'patrimonio': total_patrimonio,
            'total_pasivo_patrimonio': total_pasivos + total_patrimonio,
            'cuadrado': abs(total_activos - (total_pasivos + total_patrimonio)) < Decimal('0.01')
        }
    
    @staticmethod
    def libro_diario(
        fecha_desde: date,
        fecha_hasta: date,
        moneda: str = 'USD'
    ) -> List[Dict]:
        """
        Libro Diario para un período.
        
        Returns:
            Lista de asientos con sus detalles
        """
        campo_debe = 'debe_bsd' if moneda == 'BSD' else 'debe'
        campo_haber = 'haber_bsd' if moneda == 'BSD' else 'haber'
        
        asientos = AsientoContable.objects.filter(
            fecha_contable__range=(fecha_desde, fecha_hasta),
            estado=AsientoContable.EstadoAsiento.CONTABILIZADO
        ).order_by('fecha_contable', 'numero_asiento')
        
        resultado = []
        
        for asiento in asientos:
            detalles = []
            for detalle in asiento.detalles_asiento.all():
                debe = getattr(detalle, campo_debe)
                haber = getattr(detalle, campo_haber)
                
                detalles.append({
                    'cuenta_codigo': detalle.cuenta_contable.codigo_cuenta,
                    'cuenta_nombre': detalle.cuenta_contable.nombre_cuenta,
                    'debe': debe,
                    'haber': haber,
                    'descripcion': detalle.descripcion_linea
                })
            
            resultado.append({
                'numero': asiento.numero_asiento,
                'fecha': asiento.fecha_contable,
                'descripcion': asiento.descripcion_general,
                'tipo': asiento.get_tipo_asiento_display(),
                'detalles': detalles,
                'total_debe': asiento.total_debe if moneda == 'USD' else sum(d['debe'] for d in detalles),
                'total_haber': asiento.total_haber if moneda == 'USD' else sum(d['haber'] for d in detalles)
            })
        
        return resultado
    
    @staticmethod
    def libro_mayor(
        cuenta_id: int,
        fecha_desde: date,
        fecha_hasta: date,
        moneda: str = 'USD'
    ) -> Dict:
        """
        Libro Mayor para una cuenta específica.
        
        Returns:
            Dict con movimientos y saldo de la cuenta
        """
        campo_debe = 'debe_bsd' if moneda == 'BSD' else 'debe'
        campo_haber = 'haber_bsd' if moneda == 'BSD' else 'haber'
        
        cuenta = PlanContable.objects.get(id_cuenta=cuenta_id)
        
        # Saldo inicial (antes del período)
        saldo_inicial_data = DetalleAsiento.objects.filter(
            cuenta_contable=cuenta,
            asiento__fecha_contable__lt=fecha_desde,
            asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO
        ).aggregate(
            debe=Sum(campo_debe),
            haber=Sum(campo_haber)
        )
        
        saldo_inicial = (saldo_inicial_data['debe'] or Decimal('0')) - (saldo_inicial_data['haber'] or Decimal('0'))
        
        # Movimientos del período
        movimientos = DetalleAsiento.objects.filter(
            cuenta_contable=cuenta,
            asiento__fecha_contable__range=(fecha_desde, fecha_hasta),
            asiento__estado=AsientoContable.EstadoAsiento.CONTABILIZADO
        ).select_related('asiento').order_by('asiento__fecha_contable')
        
        detalle_movimientos = []
        saldo_acumulado = saldo_inicial
        
        for mov in movimientos:
            debe = getattr(mov, campo_debe)
            haber = getattr(mov, campo_haber)
            saldo_acumulado += debe - haber
            
            detalle_movimientos.append({
                'fecha': mov.asiento.fecha_contable,
                'asiento': mov.asiento.numero_asiento,
                'descripcion': mov.descripcion_linea or mov.asiento.descripcion_general,
                'debe': debe,
                'haber': haber,
                'saldo': saldo_acumulado
            })
        
        return {
            'cuenta': {
                'codigo': cuenta.codigo_cuenta,
                'nombre': cuenta.nombre_cuenta,
                'naturaleza': cuenta.get_naturaleza_display()
            },
            'periodo': {'desde': fecha_desde, 'hasta': fecha_hasta},
            'moneda': moneda,
            'saldo_inicial': saldo_inicial,
            'movimientos': detalle_movimientos,
            'saldo_final': saldo_acumulado
        }

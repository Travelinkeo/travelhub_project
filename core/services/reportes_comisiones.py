"""
Sistema de reportes de comisiones por aerolínea
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Q
from core.models.boletos import BoletoImportado

logger = logging.getLogger(__name__)


def generar_reporte_comisiones(fecha_inicio=None, fecha_fin=None):
    """
    Genera reporte de comisiones por aerolínea
    
    Returns:
        dict: {
            'periodo': {...},
            'por_aerolinea': [...],
            'totales': {...}
        }
    """
    # Fechas por defecto: mes actual
    if not fecha_inicio:
        fecha_inicio = datetime.now().replace(day=1).date()
    if not fecha_fin:
        fecha_fin = datetime.now().date()
    
    # Obtener boletos del período
    boletos = BoletoImportado.objects.filter(
        fecha_emision_boleto__range=[fecha_inicio, fecha_fin],
        estado_parseo='COM'
    ).exclude(aerolinea_emisora__isnull=True)
    
    # Agrupar por aerolínea
    reporte_por_aerolinea = {}
    
    for boleto in boletos:
        aerolinea = boleto.aerolinea_emisora.upper().strip()
        
        if aerolinea not in reporte_por_aerolinea:
            reporte_por_aerolinea[aerolinea] = {
                'aerolinea': aerolinea,
                'cantidad_boletos': 0,
                'total_ventas': Decimal('0.00'),
                'total_comisiones': Decimal('0.00'),
                'comision_promedio': Decimal('0.00')
            }
        
        reporte_por_aerolinea[aerolinea]['cantidad_boletos'] += 1
        
        if boleto.total_boleto:
            reporte_por_aerolinea[aerolinea]['total_ventas'] += boleto.total_boleto
        
        if boleto.comision_agencia:
            reporte_por_aerolinea[aerolinea]['total_comisiones'] += boleto.comision_agencia
    
    # Calcular promedios y ordenar
    lista_aerolineas = []
    for datos in reporte_por_aerolinea.values():
        if datos['cantidad_boletos'] > 0:
            datos['comision_promedio'] = datos['total_comisiones'] / datos['cantidad_boletos']
        lista_aerolineas.append(datos)
    
    # Ordenar por total de comisiones (descendente)
    lista_aerolineas.sort(key=lambda x: x['total_comisiones'], reverse=True)
    
    # Calcular totales generales
    totales = {
        'total_boletos': sum(a['cantidad_boletos'] for a in lista_aerolineas),
        'total_ventas': sum(a['total_ventas'] for a in lista_aerolineas),
        'total_comisiones': sum(a['total_comisiones'] for a in lista_aerolineas)
    }
    
    return {
        'periodo': {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        },
        'por_aerolinea': lista_aerolineas,
        'totales': totales
    }


def generar_reporte_comparativo(meses=3):
    """
    Genera reporte comparativo de últimos N meses
    """
    reportes_mensuales = []
    
    for i in range(meses):
        # Calcular primer y último día del mes
        fecha_fin = datetime.now().replace(day=1) - timedelta(days=i*30)
        fecha_inicio = fecha_fin.replace(day=1)
        
        # Último día del mes
        if fecha_fin.month == 12:
            fecha_fin = fecha_fin.replace(year=fecha_fin.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fecha_fin = fecha_fin.replace(month=fecha_fin.month + 1, day=1) - timedelta(days=1)
        
        reporte = generar_reporte_comisiones(fecha_inicio, fecha_fin)
        reporte['mes'] = fecha_inicio.strftime('%B %Y')
        reportes_mensuales.append(reporte)
    
    return reportes_mensuales


def obtener_top_aerolineas(limite=10, fecha_inicio=None, fecha_fin=None):
    """
    Obtiene las aerolíneas más rentables
    """
    reporte = generar_reporte_comisiones(fecha_inicio, fecha_fin)
    return reporte['por_aerolinea'][:limite]

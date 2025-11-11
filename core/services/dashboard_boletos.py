"""
Dashboard de métricas de boletos en tiempo real
"""
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from core.models.boletos import BoletoImportado


def obtener_metricas_boletos():
    """Obtiene métricas en tiempo real de boletos"""
    hoy = timezone.now().date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)
    
    # Boletos procesados
    boletos_hoy = BoletoImportado.objects.filter(fecha_subida__date=hoy).count()
    boletos_semana = BoletoImportado.objects.filter(fecha_subida__date__gte=inicio_semana).count()
    boletos_mes = BoletoImportado.objects.filter(fecha_subida__date__gte=inicio_mes).count()
    
    # Tasa de éxito por GDS
    tasas_gds = BoletoImportado.objects.values('formato_detectado').annotate(
        total=Count('id_boleto_importado'),
        exitosos=Count('id_boleto_importado', filter=Q(estado_parseo='COM')),
    )
    
    for tasa in tasas_gds:
        tasa['tasa_exito'] = (tasa['exitosos'] / tasa['total'] * 100) if tasa['total'] > 0 else 0
    
    # Tiempo promedio de procesamiento (estimado por estado)
    pendientes = BoletoImportado.objects.filter(estado_parseo='PEN').count()
    errores = BoletoImportado.objects.filter(estado_parseo='ERR').count()
    
    # Top aerolíneas del mes
    top_aerolineas = BoletoImportado.objects.filter(
        fecha_emision_boleto__gte=inicio_mes,
        estado_parseo='COM'
    ).values('aerolinea_emisora').annotate(
        cantidad=Count('id_boleto_importado')
    ).order_by('-cantidad')[:5]
    
    return {
        'procesados': {
            'hoy': boletos_hoy,
            'semana': boletos_semana,
            'mes': boletos_mes
        },
        'tasas_exito_gds': list(tasas_gds),
        'pendientes': pendientes,
        'errores': errores,
        'top_aerolineas': list(top_aerolineas)
    }

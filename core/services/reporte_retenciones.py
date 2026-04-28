# core/services/reporte_retenciones.py
"""
Servicio para generar reportes de Retenciones ISLR
"""
from datetime import datetime
from decimal import Decimal
from django.db.models import Sum, Count, Q
from core.models.retenciones_islr import RetencionISLR


class ReporteRetencionesService:
    """Generador de reportes de retenciones ISLR"""
    
    @staticmethod
    def reporte_periodo(fecha_inicio, fecha_fin, estado=None):
        """
        Genera reporte de retenciones para un período
        
        Args:
            fecha_inicio: date
            fecha_fin: date
            estado: str - Filtrar por estado (opcional)
        
        Returns:
            dict con reporte de retenciones
        """
        # Filtrar retenciones
        retenciones = RetencionISLR.objects.filter(
            fecha_emision__gte=fecha_inicio,
            fecha_emision__lte=fecha_fin
        ).select_related('factura', 'cliente').order_by('fecha_emision', 'numero_comprobante')
        
        if estado:
            retenciones = retenciones.filter(estado=estado)
        
        # Agrupar por tipo de operación
        por_tipo = {}
        for tipo_code, tipo_name in RetencionISLR.TipoOperacion.choices:
            retenciones_tipo = retenciones.filter(tipo_operacion=tipo_code)
            if retenciones_tipo.exists():
                por_tipo[tipo_name] = {
                    'cantidad': retenciones_tipo.count(),
                    'base_imponible': retenciones_tipo.aggregate(Sum('base_imponible'))['base_imponible__sum'] or Decimal('0.00'),
                    'monto_retenido': retenciones_tipo.aggregate(Sum('monto_retenido'))['monto_retenido__sum'] or Decimal('0.00'),
                }
        
        # Totales
        totales = retenciones.aggregate(
            total_retenciones=Count('id_retencion'),
            total_base_imponible=Sum('base_imponible'),
            total_retenido=Sum('monto_retenido')
        )
        
        # Detalle
        detalle = []
        for retencion in retenciones:
            detalle.append({
                'numero_comprobante': retencion.numero_comprobante,
                'fecha_emision': retencion.fecha_emision,
                'cliente': f"{retencion.cliente.nombres} {retencion.cliente.apellidos}".strip() or retencion.cliente.nombre_empresa,
                'factura': retencion.factura.numero_factura,
                'tipo_operacion': retencion.get_tipo_operacion_display(),
                'base_imponible': retencion.base_imponible,
                'porcentaje': retencion.porcentaje_retencion,
                'monto_retenido': retencion.monto_retenido,
                'estado': retencion.get_estado_display(),
            })
        
        return {
            'periodo': {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
            },
            'por_tipo_operacion': por_tipo,
            'totales': {
                'cantidad': totales['total_retenciones'] or 0,
                'base_imponible': totales['total_base_imponible'] or Decimal('0.00'),
                'monto_retenido': totales['total_retenido'] or Decimal('0.00'),
            },
            'detalle': detalle,
        }
    
    @staticmethod
    def exportar_csv(reporte):
        """Exporta reporte a CSV"""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output, delimiter=';')
        
        # Encabezado
        writer.writerow([
            'Número Comprobante', 'Fecha Emisión', 'Cliente', 'Factura',
            'Tipo Operación', 'Base Imponible', 'Porcentaje', 'Monto Retenido', 'Estado'
        ])
        
        # Detalle
        for item in reporte['detalle']:
            writer.writerow([
                item['numero_comprobante'],
                item['fecha_emision'].strftime('%d/%m/%Y'),
                item['cliente'],
                item['factura'],
                item['tipo_operacion'],
                f"{item['base_imponible']:.2f}",
                f"{item['porcentaje']:.2f}",
                f"{item['monto_retenido']:.2f}",
                item['estado'],
            ])
        
        # Totales
        writer.writerow([])
        writer.writerow(['TOTALES'])
        writer.writerow([
            '', '', '', '', '',
            f"{reporte['totales']['base_imponible']:.2f}",
            '',
            f"{reporte['totales']['monto_retenido']:.2f}",
            ''
        ])
        
        return output.getvalue()

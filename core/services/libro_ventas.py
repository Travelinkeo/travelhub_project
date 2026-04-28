# core/services/libro_ventas.py
"""
Servicio para generar Libro de Ventas según normativa SENIAT
Cumple con Providencia 0071 y formato requerido para declaración de IVA
"""
from decimal import Decimal
from datetime import date
from django.db.models import Q, Sum
from core.models import FacturaConsolidada


class LibroVentasService:
    """Generador de Libro de Ventas para IVA"""
    
    @staticmethod
    def generar_libro_ventas(fecha_inicio, fecha_fin, agencia=None):
        """
        Genera el libro de ventas para un período
        
        Args:
            fecha_inicio: date - Fecha inicial del período
            fecha_fin: date - Fecha final del período
            agencia: Agencia - Filtrar por agencia (opcional)
        
        Returns:
            dict con estructura del libro de ventas
        """
        # Filtrar facturas del período
        facturas = FacturaConsolidada.objects.filter(
            fecha_emision__gte=fecha_inicio,
            fecha_emision__lte=fecha_fin,
            estado__in=['EMI', 'PAR', 'PAG']  # Solo emitidas y pagadas
        ).select_related('cliente', 'moneda').order_by('fecha_emision', 'numero_factura')
        
        if agencia:
            facturas = facturas.filter(venta_asociada__agencia=agencia)
        
        # Separar por tipo de operación
        ventas_propias = []
        ventas_terceros = []
        
        totales = {
            'propias': {
                'base_gravada': Decimal('0.00'),
                'base_exenta': Decimal('0.00'),
                'base_exportacion': Decimal('0.00'),
                'iva_16': Decimal('0.00'),
                'iva_adicional': Decimal('0.00'),
                'igtf': Decimal('0.00'),
                'total': Decimal('0.00'),
            },
            'terceros': {
                'base_exenta': Decimal('0.00'),
                'total': Decimal('0.00'),
            }
        }
        
        for factura in facturas:
            registro = {
                'fecha': factura.fecha_emision,
                'numero_factura': factura.numero_factura,
                'numero_control': factura.numero_control,
                'cliente_rif': factura.cliente_identificacion,
                'cliente_nombre': f"{factura.cliente.nombres} {factura.cliente.apellidos}".strip() or factura.cliente.nombre_empresa,
                'base_gravada': factura.subtotal_base_gravada,
                'base_exenta': factura.subtotal_exento,
                'base_exportacion': factura.subtotal_exportacion,
                'iva_16': factura.monto_iva_16,
                'iva_adicional': factura.monto_iva_adicional,
                'igtf': factura.monto_igtf,
                'total': factura.monto_total,
                'tipo_operacion': factura.get_tipo_operacion_display(),
            }
            
            if factura.tipo_operacion == 'INTERMEDIACION' and factura.tercero_rif:
                # Factura por cuenta de terceros
                registro['tercero_rif'] = factura.tercero_rif
                registro['tercero_nombre'] = factura.tercero_razon_social
                ventas_terceros.append(registro)
                
                totales['terceros']['base_exenta'] += factura.subtotal_exento
                totales['terceros']['total'] += factura.monto_total
            else:
                # Venta propia
                ventas_propias.append(registro)
                
                totales['propias']['base_gravada'] += factura.subtotal_base_gravada
                totales['propias']['base_exenta'] += factura.subtotal_exento
                totales['propias']['base_exportacion'] += factura.subtotal_exportacion
                totales['propias']['iva_16'] += factura.monto_iva_16
                totales['propias']['iva_adicional'] += factura.monto_iva_adicional
                totales['propias']['igtf'] += factura.monto_igtf
                totales['propias']['total'] += factura.monto_total
        
        return {
            'periodo': {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
            },
            'ventas_propias': ventas_propias,
            'ventas_terceros': ventas_terceros,
            'totales': totales,
            'resumen': {
                'total_facturas': len(ventas_propias) + len(ventas_terceros),
                'facturas_propias': len(ventas_propias),
                'facturas_terceros': len(ventas_terceros),
                'debito_fiscal': totales['propias']['iva_16'] + totales['propias']['iva_adicional'],
            }
        }
    
    @staticmethod
    def exportar_csv(libro_ventas):
        """
        Exporta el libro de ventas a formato CSV para SENIAT
        
        Args:
            libro_ventas: dict - Resultado de generar_libro_ventas()
        
        Returns:
            str - Contenido CSV
        """
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output, delimiter=';')
        
        # Encabezado
        writer.writerow([
            'Fecha', 'Número Factura', 'Número Control', 'RIF Cliente', 'Nombre Cliente',
            'Base Gravada', 'Base Exenta', 'Base Exportación', 'IVA 16%', 'IVA Adicional',
            'IGTF', 'Total', 'Tipo Operación', 'RIF Tercero', 'Nombre Tercero'
        ])
        
        # Ventas propias
        for venta in libro_ventas['ventas_propias']:
            writer.writerow([
                venta['fecha'].strftime('%d/%m/%Y'),
                venta['numero_factura'],
                venta['numero_control'],
                venta['cliente_rif'],
                venta['cliente_nombre'],
                f"{venta['base_gravada']:.2f}",
                f"{venta['base_exenta']:.2f}",
                f"{venta['base_exportacion']:.2f}",
                f"{venta['iva_16']:.2f}",
                f"{venta['iva_adicional']:.2f}",
                f"{venta['igtf']:.2f}",
                f"{venta['total']:.2f}",
                venta['tipo_operacion'],
                '',
                ''
            ])
        
        # Ventas por cuenta de terceros
        for venta in libro_ventas['ventas_terceros']:
            writer.writerow([
                venta['fecha'].strftime('%d/%m/%Y'),
                venta['numero_factura'],
                venta['numero_control'],
                venta['cliente_rif'],
                venta['cliente_nombre'],
                f"{venta['base_gravada']:.2f}",
                f"{venta['base_exenta']:.2f}",
                f"{venta['base_exportacion']:.2f}",
                f"{venta['iva_16']:.2f}",
                f"{venta['iva_adicional']:.2f}",
                f"{venta['igtf']:.2f}",
                f"{venta['total']:.2f}",
                venta['tipo_operacion'],
                venta.get('tercero_rif', ''),
                venta.get('tercero_nombre', '')
            ])
        
        # Totales
        writer.writerow([])
        writer.writerow(['TOTALES VENTAS PROPIAS'])
        writer.writerow([
            '', '', '', '', '',
            f"{libro_ventas['totales']['propias']['base_gravada']:.2f}",
            f"{libro_ventas['totales']['propias']['base_exenta']:.2f}",
            f"{libro_ventas['totales']['propias']['base_exportacion']:.2f}",
            f"{libro_ventas['totales']['propias']['iva_16']:.2f}",
            f"{libro_ventas['totales']['propias']['iva_adicional']:.2f}",
            f"{libro_ventas['totales']['propias']['igtf']:.2f}",
            f"{libro_ventas['totales']['propias']['total']:.2f}",
        ])
        
        writer.writerow([])
        writer.writerow(['TOTALES VENTAS POR CUENTA DE TERCEROS'])
        writer.writerow([
            '', '', '', '', '',
            '0.00',
            f"{libro_ventas['totales']['terceros']['base_exenta']:.2f}",
            '0.00', '0.00', '0.00', '0.00',
            f"{libro_ventas['totales']['terceros']['total']:.2f}",
        ])
        
        writer.writerow([])
        writer.writerow(['DÉBITO FISCAL TOTAL (IVA A DECLARAR)'])
        writer.writerow(['', '', '', '', '', '', '', '',
            f"{libro_ventas['resumen']['debito_fiscal']:.2f}"
        ])
        
        return output.getvalue()

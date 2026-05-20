import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from apps.bookings.models.importacion import BoletoImportado
from apps.bookings.models.venta import Venta
from apps.finance.models import Factura, ItemFactura

logger = logging.getLogger(__name__)

class InvoicingService:
    @staticmethod
    @transaction.atomic
    def create_invoice_from_venta(venta_id, agencia):
        """
        Genera una factura a partir de una venta.
        Aplica la lógica de 'Fees Ocultos' sumándolos al primer item.
        """
        venta = Venta.objects.select_related('cliente', 'moneda').get(pk=venta_id, agencia=agencia)
        
        if not venta.cliente:
            raise ValidationError(_("La venta debe tener un cliente asignado para facturar."))
            
        if Factura.objects.filter(venta_asociada=venta).exists():
            raise ValidationError(_("Esta venta ya tiene una factura asociada."))

        # 1. Crear la cabecera de la factura
        factura = Factura.objects.create(
            agencia=agencia,
            cliente=venta.cliente,
            moneda=venta.moneda,
            venta_asociada=venta,
            tipo_operacion=Factura.TipoOperacion.INTERMEDIACION if venta.items_venta.filter(tipo_item='AIR').exists() else Factura.TipoOperacion.VENTA_PROPIA,
            moneda_operacion=Factura.MonedaOperacion.DIVISA if venta.moneda.codigo == 'USD' else Factura.MonedaOperacion.BOLIVAR,
            tasa_cambio_bcv=Decimal('0.00'), # Placeholder, debería venir del mercado
        )

        # 2. Calcular fees totales para distribuir
        total_fees = venta.fees_venta.aggregate(Sum('monto'))['monto__sum'] or Decimal('0.00')

        # 3. Procesar items
        items_venta = venta.items_venta.select_related('producto_servicio').all()
        boleto = BoletoImportado.objects.filter(venta_asociada=venta).first()
        
        total_items = items_venta.count()
        
        for i, item_venta in enumerate(items_venta):
            descripcion = item_venta.descripcion_personalizada or item_venta.producto_servicio.nombre
            
            # Enriquecer descripción si es aéreo
            if not item_venta.descripcion_personalizada and item_venta.producto_servicio.tipo_producto == 'AIR' and boleto:
                descripcion = f"Boleto Aéreo: {boleto.ruta_vuelo or ''}"
                if boleto.numero_boleto:
                    descripcion += f" ({boleto.numero_boleto})"
            
            precio_unitario = item_venta.precio_unitario_venta
            
            # LÓGICA DE FEES OCULTOS: Sumar al primer item
            if i == 0 and total_items > 0:
                precio_unitario += total_fees
            
            # Mapear tipo de servicio para la factura consolidada
            tipo_servicio = ItemFactura.TipoServicio.ALOJAMIENTO_Y_OTROS_GRAVADOS
            if item_venta.producto_servicio.tipo_producto == 'AIR':
                tipo_servicio = ItemFactura.TipoServicio.TRANSPORTE_AEREO_NACIONAL # O Internacional
            
            ItemFactura.objects.create(
                factura=factura,
                descripcion=descripcion,
                cantidad=item_venta.cantidad,
                precio_unitario=precio_unitario,
                tipo_servicio=tipo_servicio,
                es_gravado=item_venta.impuestos_item_venta > 0,
                # Datos de boleto si aplica
                nombre_pasajero=boleto.nombre_pasajero if boleto else "",
                numero_boleto=boleto.numero_boleto if boleto else "",
                itinerario=boleto.ruta_vuelo if boleto else "",
            )

        # 4. Recalcular totales finales
        InvoicingService.recalculate_invoice_totals(factura.pk)
        
        return factura

    @staticmethod
    def recalculate_invoice_totals(factura_id):
        """
        Recalcula los totales de una factura sumando sus items.
        Esta es una operación pesada que se centraliza aquí.
        """
        factura = Factura.objects.get(pk=factura_id)
        items = factura.items_factura.all()
        
        subtotal_base_gravada = Decimal('0.00')
        subtotal_exento = Decimal('0.00')
        subtotal_exportacion = Decimal('0.00')
        monto_iva_16 = Decimal('0.00')
        
        for item in items:
            if item.tipo_servicio == ItemFactura.TipoServicio.SERVICIO_EXPORTACION:
                subtotal_exportacion += item.subtotal_item
            elif item.tipo_servicio == ItemFactura.TipoServicio.TRANSPORTE_AEREO_NACIONAL:
                subtotal_exento += item.subtotal_item
            else:
                if item.es_gravado:
                    subtotal_base_gravada += item.subtotal_item
                    monto_iva_16 += item.subtotal_item * (item.alicuota_iva / 100)
                else:
                    subtotal_exento += item.subtotal_item
        
        # Actualizar campos
        factura.subtotal_base_gravada = subtotal_base_gravada
        factura.subtotal_exento = subtotal_exento
        factura.subtotal_exportacion = subtotal_exportacion
        factura.monto_iva_16 = monto_iva_16
        
        # El .save() del modelo Factura ya calcula subtotal, monto_total y equivalencias en Bs.
        factura.save()

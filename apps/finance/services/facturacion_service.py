"""Servicio de facturacion service para la aplicación finance.
"""

import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.bookings.models import BoletoImportado, Venta
from apps.finance.models import Factura, ItemFactura
from apps.finance.services.bcv_service import obtener_tasa_bcv_resiliente

logger = logging.getLogger(__name__)


def obtener_itinerario_limpio(ruta_vuelo):
    # obtener_itinerario_limpio: Obtener itinerario limpio. Args: según implementación. Returns: según implementación.
    if not ruta_vuelo:
        return ""
    ruta_vuelo_str = str(ruta_vuelo).strip()
    if ruta_vuelo_str.startswith("[") or ruta_vuelo_str.startswith("{"):
        import json

        try:
            segments = json.loads(ruta_vuelo_str)
            if isinstance(segments, list):
                route_parts = []
                for seg in segments:
                    orig = seg.get("codigo_iata_origen") or seg.get("origen")
                    dest = seg.get("codigo_iata_destino") or seg.get("destino")
                    if orig and (not route_parts or route_parts[-1] != orig):
                        route_parts.append(str(orig))
                    if dest:
                        route_parts.append(str(dest))
                if route_parts:
                    return "-".join(route_parts)
        except (AttributeError, TypeError, KeyError):
            pass
    return ruta_vuelo_str


class FacturacionService:
    """
    Servicio unificado para la generación y gestión de facturas fiscales.
    Centraliza el cálculo de impuestos venezolanos (IVA 25%, IGTF 3%, INATUR 1%).
    """

    @staticmethod
    @transaction.atomic
    def generar_factura_desde_venta(venta: Venta, cliente=None) -> Factura:
        """
        Genera una Factura Fiscal a partir de una Venta.
        Aplica tasas de cambio dinámicas de BCV e independiza la línea de fees de gestión.
        """
        cliente_final = cliente or venta.cliente
        if not cliente_final:
            raise ValidationError(_("La venta debe tener un cliente asignado para facturar."))

        # 3. Obtener tasa BCV resiliente (ya retorna Decimal)
        tasa_bcv = obtener_tasa_bcv_resiliente("USD")
        if tasa_bcv <= 0:
            tasa_bcv = Decimal("1.00")

        # 4. Crear cabecera de la factura en estado BORRADOR
        factura = Factura.objects.create(
            agencia=venta.agencia,
            cliente=cliente_final,
            fecha_emision=timezone.localtime(timezone.now()).date(),
            tasa_bcv_aplicada=tasa_bcv,
            estado=Factura.EstadoFactura.BORRADOR,
        )

        # 6. Crear ítems de factura correspondientes a la venta
        boleto = BoletoImportado.objects.filter(venta_asociada=venta).first()
        for item_venta in venta.items_venta.select_related("producto_servicio").all():
            descripcion = item_venta.descripcion_personalizada or (
                item_venta.producto_servicio.nombre
                if item_venta.producto_servicio
                else _("Servicios Turísticos")
            )

            if item_venta.tipo_item == "AIR" or (
                item_venta.producto_servicio and item_venta.producto_servicio.tipo_producto == "AIR"
            ):
                if boleto:
                    itinerario_limpio = obtener_itinerario_limpio(boleto.ruta_vuelo)
                    descripcion = f"Boleto Aéreo: {itinerario_limpio}"
                    if boleto.numero_boleto:
                        descripcion += f" ({boleto.numero_boleto})"
                    descripcion = descripcion[:500]

            exento = not (item_venta.impuestos_item_venta > 0 or item_venta.tipo_item != "AIR")

            ItemFactura.objects.create(
                agencia=factura.agencia,
                factura=factura,
                descripcion=descripcion,
                cantidad=item_venta.cantidad,
                precio_unitario_usd=item_venta.precio_unitario_venta,
                exento=exento,
            )

        # 7. Desglosar Fees como ítem independiente
        total_fees = venta.fees_venta.aggregate(s=Sum("monto"))["s"] or Decimal("0.00")
        if total_fees > 0:
            ItemFactura.objects.create(
                agencia=factura.agencia,
                factura=factura,
                descripcion=f"Servicio de Gestión y Emisión - {venta.localizador or venta.pk}",
                cantidad=1,
                precio_unitario_usd=total_fees,
                exento=False,
            )

        logger.info(f"Factura {factura.numero_control} generada exitosamente (ID: {factura.pk}).")
        return factura

    @staticmethod
    def recalculate_invoice_totals(factura_id):
        """
        Recalcula los totales de una factura llamando a su lógica nativa de impuestos de Venezuela.
        """
        factura = Factura.objects.get(pk=factura_id)
        factura.save()
        return factura

    @staticmethod
    @transaction.atomic
    def actualizar_factura_desde_venta(factura: Factura, venta=None) -> None:
        """
        Sincroniza los ítems y totales de una factura en estado BORRADOR
        con los ítems y fees actuales de su venta asociada.
        """
        if not venta:
            return
        if factura.estado in {Factura.EstadoFactura.EMITIDA, Factura.EstadoFactura.ANULADA}:
            return

        # 1. Eliminar ítems existentes de la factura
        factura.items.all().delete()

        # 2. Recrear ítems de factura a partir de los items de venta
        for item_venta in venta.items_venta.select_related("producto_servicio").all():
            descripcion = item_venta.descripcion_personalizada or (
                item_venta.producto_servicio.nombre
                if item_venta.producto_servicio
                else "Servicios Turísticos"
            )

            if item_venta.tipo_item == "AIR" or (
                item_venta.producto_servicio and item_venta.producto_servicio.tipo_producto == "AIR"
            ):
                boleto = BoletoImportado.objects.filter(venta_asociada=venta).first()
                if boleto:
                    itinerario_limpio = obtener_itinerario_limpio(boleto.ruta_vuelo)
                    descripcion = f"Boleto Aéreo: {itinerario_limpio}"
                    if boleto.numero_boleto:
                        descripcion += f" ({boleto.numero_boleto})"
                    descripcion = descripcion[:500]

            exento = not (item_venta.impuestos_item_venta > 0 or item_venta.tipo_item != "AIR")

            ItemFactura.objects.create(
                agencia=factura.agencia,
                factura=factura,
                descripcion=descripcion,
                cantidad=item_venta.cantidad,
                precio_unitario_usd=item_venta.precio_unitario_venta,
                exento=exento,
            )

        # 3. Recrear fee si existe
        total_fees = venta.fees_venta.aggregate(s=Sum("monto"))["s"] or Decimal("0.00")
        if total_fees > 0:
            ItemFactura.objects.create(
                agencia=factura.agencia,
                factura=factura,
                descripcion=f"Servicio de Gestión y Emisión - {venta.localizador or venta.pk}",
                cantidad=1,
                precio_unitario_usd=total_fees,
                exento=False,
            )

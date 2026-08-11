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
    """obtener_itinerario_limpio."""
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

        from apps.finance.models import generar_numero_factura_atomico

        fecha_emision = timezone.localtime(timezone.now()).date()
        num_control = generar_numero_factura_atomico(Factura, fecha_emision)

        # 4. Crear cabecera de la factura en estado BORRADOR
        factura = Factura.objects.create(
            agencia=venta.agencia,
            cliente=cliente_final,
            fecha_emision=fecha_emision,
            numero_control=num_control,
            tasa_bcv_aplicada=tasa_bcv,
            estado=Factura.EstadoFactura.BORRADOR,
        )

        # 6. Crear ítems de factura correspondientes a todos los boletos del localizador (PNR)
        boletos_asociados = list(BoletoImportado.objects.filter(venta_asociada=venta))
        if boletos_asociados:
            for boleto in boletos_asociados:
                itinerario_limpio = obtener_itinerario_limpio(boleto.ruta_vuelo)
                pax_nombre = (
                    boleto.nombre_pasajero_procesado or boleto.nombre_pasajero_completo or ""
                )
                pax_str = f" - PAX: {pax_nombre}" if pax_nombre else ""
                desc = (
                    f"Boleto Aéreo: {itinerario_limpio} ({boleto.numero_boleto or 'S/N'}){pax_str}"[
                        :500
                    ]
                )
                monto_boleto = boleto.total_boleto or boleto.tarifa_base or Decimal("0.00")
                monto_ves = (monto_boleto * tasa_bcv).quantize(Decimal("0.01"))

                ItemFactura.objects.create(
                    agencia=factura.agencia,
                    factura=factura,
                    descripcion=desc,
                    cantidad=1,
                    precio_unitario_usd=monto_boleto,
                    precio_unitario_ves=monto_ves,
                    total_linea_usd=monto_boleto,
                    total_linea_ves=monto_ves,
                    exento=True,  # Pasaje pasante por cuenta de terceros (TSJ 00256)
                )

        # 6b. Crear ítems para otros productos/servicios no aéreos
        for item_venta in (
            venta.items_venta.select_related("producto_servicio").exclude(tipo_item="AIR").all()
        ):
            descripcion = item_venta.descripcion_personalizada or (
                item_venta.producto_servicio.nombre
                if item_venta.producto_servicio
                else _("Servicios Turísticos")
            )
            pu_usd = item_venta.precio_unitario_venta or Decimal("0.00")
            pu_ves = (pu_usd * tasa_bcv).quantize(Decimal("0.01"))
            tot_usd = (pu_usd * item_venta.cantidad).quantize(Decimal("0.01"))
            tot_ves = (pu_ves * item_venta.cantidad).quantize(Decimal("0.01"))
            ItemFactura.objects.create(
                agencia=factura.agencia,
                factura=factura,
                descripcion=descripcion,
                cantidad=item_venta.cantidad,
                precio_unitario_usd=pu_usd,
                precio_unitario_ves=pu_ves,
                total_linea_usd=tot_usd,
                total_linea_ves=tot_ves,
                exento=False,
            )

        # 6c. Fallback si no existen registros BoletoImportado pero hay items_venta de tipo AIR
        if not boletos_asociados:
            for item_venta in (
                venta.items_venta.filter(tipo_item="AIR").select_related("producto_servicio").all()
            ):
                descripcion = item_venta.descripcion_personalizada or (
                    item_venta.producto_servicio.nombre
                    if item_venta.producto_servicio
                    else _("Boleto Aéreo")
                )
                pu_usd = item_venta.precio_unitario_venta or Decimal("0.00")
                pu_ves = (pu_usd * tasa_bcv).quantize(Decimal("0.01"))
                tot_usd = (pu_usd * item_venta.cantidad).quantize(Decimal("0.01"))
                tot_ves = (pu_ves * item_venta.cantidad).quantize(Decimal("0.01"))
                ItemFactura.objects.create(
                    agencia=factura.agencia,
                    factura=factura,
                    descripcion=descripcion,
                    cantidad=item_venta.cantidad,
                    precio_unitario_usd=pu_usd,
                    precio_unitario_ves=pu_ves,
                    total_linea_usd=tot_usd,
                    total_linea_ves=tot_ves,
                    exento=True,
                )

        # 7. Desglosar Fees como ítem independiente
        total_fees = venta.fees_venta.aggregate(s=Sum("monto"))["s"] or Decimal("0.00")
        if total_fees > 0:
            fee_ves = (total_fees * tasa_bcv).quantize(Decimal("0.01"))
            ItemFactura.objects.create(
                agencia=factura.agencia,
                factura=factura,
                descripcion=f"Servicio de Gestión y Emisión - {venta.localizador or venta.pk}",
                cantidad=1,
                precio_unitario_usd=total_fees,
                precio_unitario_ves=fee_ves,
                total_linea_usd=total_fees,
                total_linea_ves=fee_ves,
                exento=False,
            )

        # 8. Aplicar desglose fiscal especializado (TSJ 00256, INATUR 1%, LOCTEM 3%)
        from apps.finance.services.fiscal_service import FiscalTurismoService

        items_payload = []
        for it in factura.items.all():
            items_payload.append(
                {
                    "monto": it.precio_unitario_usd * it.cantidad,
                    "cantidad": it.cantidad,
                    "tipo": "BOLETO"
                    if ("Boleto" in it.descripcion or "Pasaje" in it.descripcion)
                    else "FEE",
                    "aplica_iva": not it.exento,
                }
            )

        desglose = FiscalTurismoService.calcular_desglose_tsj256(items_payload, tasa_bcv=tasa_bcv)
        factura.monto_cuenta_terceros_usd = desglose["monto_cuenta_terceros_usd"]
        factura.monto_cuenta_terceros_ves = desglose["monto_cuenta_terceros_ves"]
        factura.ingreso_propio_agencia_usd = desglose["ingreso_propio_agencia_usd"]
        factura.ingreso_propio_agencia_ves = desglose["ingreso_propio_agencia_ves"]
        factura.monto_inatur_1_usd = desglose["monto_inatur_1_usd"]
        factura.monto_inatur_1_ves = desglose["monto_inatur_1_ves"]
        factura.base_impuesto_municipal_usd = desglose["base_impuesto_municipal_usd"]
        factura.base_impuesto_municipal_ves = desglose["base_impuesto_municipal_ves"]
        factura.monto_impuesto_municipal_usd = desglose["monto_impuesto_municipal_usd"]
        factura.monto_impuesto_municipal_ves = desglose["monto_impuesto_municipal_ves"]
        factura.save()

        logger.info(
            f"Factura {factura.numero_control} generada exitosamente para PNR {venta.localizador} con {len(boletos_asociados)} boletos (ID: {factura.pk})."
        )
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
        con todos los boletos, ítems y fees actuales del localizador (PNR).
        """
        if not venta:
            return
        if factura.estado in {Factura.EstadoFactura.EMITIDA, Factura.EstadoFactura.ANULADA}:
            return

        # 1. Eliminar ítems existentes de la factura borrador
        factura.items.all().delete()

        # 2. Recrear ítems de factura a partir de TODOS los boletos del localizador
        boletos_asociados = list(BoletoImportado.objects.filter(venta_asociada=venta))
        if boletos_asociados:
            for boleto in boletos_asociados:
                itinerario_limpio = obtener_itinerario_limpio(boleto.ruta_vuelo)
                pax_nombre = (
                    boleto.nombre_pasajero_procesado or boleto.nombre_pasajero_completo or ""
                )
                pax_str = f" - PAX: {pax_nombre}" if pax_nombre else ""
                desc = (
                    f"Boleto Aéreo: {itinerario_limpio} ({boleto.numero_boleto or 'S/N'}){pax_str}"[
                        :500
                    ]
                )
                monto_boleto = boleto.total_boleto or boleto.tarifa_base or Decimal("0.00")

                ItemFactura.objects.create(
                    agencia=factura.agencia,
                    factura=factura,
                    descripcion=desc,
                    cantidad=1,
                    precio_unitario_usd=monto_boleto,
                    exento=True,
                )

        # 3. Recrear otros servicios no aéreos
        for item_venta in (
            venta.items_venta.select_related("producto_servicio").exclude(tipo_item="AIR").all()
        ):
            descripcion = item_venta.descripcion_personalizada or (
                item_venta.producto_servicio.nombre
                if item_venta.producto_servicio
                else "Servicios Turísticos"
            )
            ItemFactura.objects.create(
                agencia=factura.agencia,
                factura=factura,
                descripcion=descripcion,
                cantidad=item_venta.cantidad,
                precio_unitario_usd=item_venta.precio_unitario_venta,
                exento=False,
            )

        # 4. Fallback AIR items_venta
        if not boletos_asociados:
            for item_venta in (
                venta.items_venta.filter(tipo_item="AIR").select_related("producto_servicio").all()
            ):
                descripcion = item_venta.descripcion_personalizada or (
                    item_venta.producto_servicio.nombre
                    if item_venta.producto_servicio
                    else "Boleto Aéreo"
                )
                ItemFactura.objects.create(
                    agencia=factura.agencia,
                    factura=factura,
                    descripcion=descripcion,
                    cantidad=item_venta.cantidad,
                    precio_unitario_usd=item_venta.precio_unitario_venta,
                    exento=True,
                )

        # 5. Recrear fee si existe
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

        # 6. Recalcular desglose fiscal
        from apps.finance.services.fiscal_service import FiscalTurismoService

        tasa_bcv = factura.tasa_bcv_aplicada or Decimal("1.00")
        items_payload = []
        for it in factura.items.all():
            items_payload.append(
                {
                    "monto": it.precio_unitario_usd * it.cantidad,
                    "cantidad": it.cantidad,
                    "tipo": "BOLETO"
                    if ("Boleto" in it.descripcion or "Pasaje" in it.descripcion)
                    else "FEE",
                    "aplica_iva": not it.exento,
                }
            )

        desglose = FiscalTurismoService.calcular_desglose_tsj256(items_payload, tasa_bcv=tasa_bcv)
        factura.monto_cuenta_terceros_usd = desglose["monto_cuenta_terceros_usd"]
        factura.monto_cuenta_terceros_ves = desglose["monto_cuenta_terceros_ves"]
        factura.ingreso_propio_agencia_usd = desglose["ingreso_propio_agencia_usd"]
        factura.ingreso_propio_agencia_ves = desglose["ingreso_propio_agencia_ves"]
        factura.monto_inatur_1_usd = desglose["monto_inatur_1_usd"]
        factura.monto_inatur_1_ves = desglose["monto_inatur_1_ves"]
        factura.base_impuesto_municipal_usd = desglose["base_impuesto_municipal_usd"]
        factura.base_impuesto_municipal_ves = desglose["base_impuesto_municipal_ves"]
        factura.monto_impuesto_municipal_usd = desglose["monto_impuesto_municipal_usd"]
        factura.monto_impuesto_municipal_ves = desglose["monto_impuesto_municipal_ves"]
        factura.save()

    @staticmethod
    @transaction.atomic
    def generar_o_actualizar_factura_por_localizador(venta: Venta) -> Factura:
        """
        Garantiza que exista una factura única amarrada al localizador (PNR).
        Si la factura ya existe en borrador, la actualiza incorporando nuevos boletos e ítems
        tras la finalización de la ingesta por Mailbot o importación manual.

        SI LA FACTURA YA ESTÁ EMITIDA (CERRADA ANTE EL SENIAT):
        - La factura original EMITIDA NO se altera ni se modifica.
        - Los boletos re-subidos se marcan como es_reemision=True (Exchange / Remisión).
        """
        # 1. Verificar si existe una factura en estado EMITIDA para este localizador
        factura_emitida = Factura.objects.filter(
            agencia=venta.agencia,
            items__descripcion__contains=venta.localizador,
            estado=Factura.EstadoFactura.EMITIDA,
        ).first()

        if factura_emitida:
            logger.info(
                f"🔒 Factura {factura_emitida.numero_control} para PNR {venta.localizador} ya se encuentra EMITIDA. "
                f"Documento fiscal congelado. Registrando boletos posteriores como Reemisión / Remisión."
            )
            # Marcar boletos no marcados como es_reemision=True
            BoletoImportado.objects.filter(venta_asociada=venta, es_reemision=False).update(
                es_reemision=True
            )
            return factura_emitida

        # 2. Si existe una factura en BORRADOR, actualizarla
        factura_borrador = Factura.objects.filter(
            agencia=venta.agencia,
            items__descripcion__contains=venta.localizador,
            estado=Factura.EstadoFactura.BORRADOR,
        ).first()

        if not factura_borrador:
            factura_borrador = (
                Factura.objects.filter(
                    agencia=venta.agencia,
                    cliente=venta.cliente,
                    estado=Factura.EstadoFactura.BORRADOR,
                )
                .order_by("-fecha_emision", "-id")
                .first()
            )

        if factura_borrador:
            FacturacionService.actualizar_factura_desde_venta(factura_borrador, venta)
            return factura_borrador
        else:
            return FacturacionService.generar_factura_desde_venta(venta)

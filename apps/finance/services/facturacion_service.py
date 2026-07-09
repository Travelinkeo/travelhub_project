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
from apps.finance.services.tax_eligibility import es_itinerario_internacional

logger = logging.getLogger(__name__)


def obtener_itinerario_limpio(ruta_vuelo):
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

        # 1. Verificar si ya existe una factura para esta venta
        if Factura.objects.filter(venta_asociada_id=venta.pk).exists():
            raise ValidationError(_("Esta venta ya tiene una factura asociada."))

        # 2. Determinar tipo de operación y moneda
        es_aereo = venta.items_venta.filter(tipo_item="AIR").exists()
        tipo_operacion = (
            Factura.TipoOperacion.INTERMEDIACION if es_aereo else Factura.TipoOperacion.VENTA_PROPIA
        )

        moneda_codigo = venta.moneda.codigo_iso if venta.moneda else "USD"
        moneda_operacion = (
            Factura.MonedaOperacion.DIVISA
            if moneda_codigo == "USD"
            else Factura.MonedaOperacion.BOLIVAR
        )

        # 3. Obtener tasa BCV resiliente (ya retorna Decimal)
        tasa_bcv = obtener_tasa_bcv_resiliente(moneda_codigo)
        if tasa_bcv <= 0:
            tasa_bcv = Decimal("1.00")

        # 3b. Obtener boleto importado y datos del tercero si aplica (intermediación)
        boleto = BoletoImportado.objects.filter(venta_asociada=venta).first()
        tercero_rif = ""
        tercero_razon_social = ""

        if tipo_operacion == Factura.TipoOperacion.INTERMEDIACION:
            if boleto:
                proveedor_emisor = boleto.proveedor_emisor
                if not proveedor_emisor and boleto.aerolinea_emisora:
                    from apps.bookings.models import Proveedor

                    proveedor_emisor = Proveedor.objects.filter(
                        nombre__icontains=boleto.aerolinea_emisora
                    ).first()

                if proveedor_emisor:
                    tercero_rif = proveedor_emisor.rif or "J-00000000-0"
                    tercero_razon_social = proveedor_emisor.nombre or "Aerolínea Genérica"
                else:
                    tercero_razon_social = boleto.aerolinea_emisora or "Aerolínea Genérica"
                    tercero_rif = "J-00000000-0"
            else:
                # Buscar proveedor del primer item aéreo si no hay boleto importado
                primer_item = venta.items_venta.filter(tipo_item="AIR").first()
                if (
                    primer_item
                    and primer_item.producto_servicio
                    and primer_item.producto_servicio.proveedor_principal
                ):
                    prov = primer_item.producto_servicio.proveedor_principal
                    tercero_rif = prov.rif or "J-00000000-0"
                    tercero_razon_social = prov.nombre or "Aerolínea Genérica"

            # Fallbacks obligatorios finales si siguen vacíos para no fallar validación del modelo
            if not tercero_rif:
                tercero_rif = "J-00000000-0"
            if not tercero_razon_social:
                tercero_razon_social = "Aerolínea Genérica"

        # 4. Crear cabecera de la factura en estado BORRADOR
        factura = Factura.objects.create(
            agencia=venta.agencia,
            cliente=cliente_final,
            moneda=venta.moneda,
            venta_asociada=venta,
            fecha_emision=timezone.localtime(timezone.now()).date(),
            cliente_nombre=cliente_final.get_nombre_completo(),
            cliente_rif=getattr(cliente_final, "cedula_identidad", "")
            or getattr(cliente_final, "numero_pasaporte", "")
            or "",
            cliente_direccion=getattr(cliente_final, "direccion", "")
            or getattr(cliente_final, "direccion_linea1", "")
            or "",
            cliente_telefono=getattr(cliente_final, "telefono_principal", "") or "",
            tipo_operacion=tipo_operacion,
            moneda_operacion=moneda_operacion,
            tasa_cambio_bcv=tasa_bcv,
            tasa_cambio=tasa_bcv,
            tercero_rif=tercero_rif,
            tercero_razon_social=tercero_razon_social,
            estado=Factura.EstadoFactura.BORRADOR,
        )

        # 6. Crear ítems de factura correspondientes a la venta
        for item_venta in venta.items_venta.select_related("producto_servicio").all():
            descripcion = item_venta.descripcion_personalizada or (
                item_venta.producto_servicio.nombre
                if item_venta.producto_servicio
                else _("Servicios Turísticos")
            )

            # Enriquecer descripción e itinerario si es aéreo
            nombre_pasajero = ""
            numero_boleto = ""
            itinerario = ""
            codigo_aerolinea = ""

            if item_venta.tipo_item == "AIR" or (
                item_venta.producto_servicio and item_venta.producto_servicio.tipo_producto == "AIR"
            ):
                if boleto and es_itinerario_internacional(boleto):
                    tipo_servicio = ItemFactura.TipoServicio.TRANSPORTE_AEREO_INTERNACIONAL
                else:
                    tipo_servicio = ItemFactura.TipoServicio.TRANSPORTE_AEREO_NACIONAL
                if boleto:
                    itinerario_limpio = obtener_itinerario_limpio(boleto.ruta_vuelo)
                    descripcion = f"Boleto Aéreo: {itinerario_limpio}"
                    if boleto.numero_boleto:
                        descripcion += f" ({boleto.numero_boleto})"
                    descripcion = descripcion[:500]
                    nombre_pasajero = (
                        getattr(boleto, "nombre_pasajero_completo", "")
                        or getattr(boleto, "nombre_pasajero_procesado", "")
                        or ""
                    )
                    numero_boleto = boleto.numero_boleto or ""
                    itinerario = itinerario_limpio
                    codigo_aerolinea = (
                        boleto.proveedor_emisor.iata
                        if boleto.proveedor_emisor and boleto.proveedor_emisor.iata
                        else (boleto.aerolinea_emisora or "")
                    )[:10]
            else:
                tipo_servicio = ItemFactura.TipoServicio.ALOJAMIENTO_Y_OTROS_GRAVADOS

            # Lógica de alícuotas (IVA General 25% o Exento)
            es_gravado = item_venta.impuestos_item_venta > 0 or item_venta.tipo_item != "AIR"
            if es_gravado:
                tipo_impuesto = ItemFactura.TipoImpuesto.IVA_25
                alicuota_iva = Decimal("25.00")
            else:
                tipo_impuesto = ItemFactura.TipoImpuesto.EXENTO
                alicuota_iva = Decimal("0.00")

            ItemFactura.objects.create(
                agencia=factura.agencia,
                factura=factura,
                descripcion=descripcion,
                cantidad=item_venta.cantidad,
                precio_unitario=item_venta.precio_unitario_venta,
                tipo_servicio=tipo_servicio,
                es_gravado=es_gravado,
                tipo_impuesto=tipo_impuesto,
                alicuota_iva=alicuota_iva,
                nombre_pasajero=nombre_pasajero,
                numero_boleto=numero_boleto,
                itinerario=itinerario,
                codigo_aerolinea=codigo_aerolinea,
            )

        # 7. Desglosar Fees como ítem independiente gravado al 25% de IVA
        total_fees = venta.fees_venta.aggregate(s=Sum("monto"))["s"] or Decimal("0.00")
        if total_fees > 0:
            ItemFactura.objects.create(
                agencia=factura.agencia,
                factura=factura,
                descripcion=f"Servicio de Gestión y Emisión - {venta.localizador or venta.pk}",
                cantidad=1,
                precio_unitario=total_fees,
                tipo_servicio=ItemFactura.TipoServicio.ALOJAMIENTO_Y_OTROS_GRAVADOS,
                es_gravado=True,
                tipo_impuesto=ItemFactura.TipoImpuesto.IVA_25,
                alicuota_iva=Decimal("25.00"),
            )

        # Enlazar la factura a la venta
        venta.factura_id = factura.pk
        # Sincronizar también el campo factura_consolidada si existe
        if hasattr(venta, "factura_consolidada_id"):
            venta.factura_consolidada_id = factura.pk
        venta.save(
            update_fields=["factura_id", "factura_consolidada_id"]
            if hasattr(venta, "factura_consolidada_id")
            else ["factura_id"]
        )

        logger.info(
            f"Factura {factura.numero_factura} generada exitosamente (ID: {factura.pk}) con IVA 25%."
        )
        return factura

    @staticmethod
    def recalculate_invoice_totals(factura_id):
        """
        Recalcula los totales de una factura llamando a su lógica nativa de impuestos de Venezuela.
        """
        factura = Factura.objects.get(pk=factura_id)
        if hasattr(factura, "calcular_impuestos_venezuela"):
            factura.calcular_impuestos_venezuela()
        else:
            factura.recalcular_totales()
            factura.save()
        return factura

    @staticmethod
    @transaction.atomic
    def actualizar_factura_desde_venta(factura: Factura) -> None:
        """
        Sincroniza los ítems y totales de una factura en estado BORRADOR
        con los ítems y fees actuales de su venta asociada.
        """
        if not factura.venta_asociada or factura.estado in {
            Factura.EstadoFactura.PAGADA,
            Factura.EstadoFactura.ANULADA,
        }:
            return

        venta = factura.venta_asociada

        # 1. Eliminar ítems existentes de la factura
        factura.items_factura.all().hard_delete()

        # 2. Recrear ítems de factura a partir de los items de venta
        boleto = BoletoImportado.objects.filter(venta_asociada=venta).first()
        for item_venta in venta.items_venta.select_related("producto_servicio").all():
            descripcion = item_venta.descripcion_personalizada or (
                item_venta.producto_servicio.nombre
                if item_venta.producto_servicio
                else "Servicios Turísticos"
            )

            nombre_pasajero = ""
            numero_boleto = ""
            itinerario = ""
            codigo_aerolinea = ""

            if item_venta.tipo_item == "AIR" or (
                item_venta.producto_servicio and item_venta.producto_servicio.tipo_producto == "AIR"
            ):
                if boleto and es_itinerario_internacional(boleto):
                    tipo_servicio = ItemFactura.TipoServicio.TRANSPORTE_AEREO_INTERNACIONAL
                else:
                    tipo_servicio = ItemFactura.TipoServicio.TRANSPORTE_AEREO_NACIONAL
                if boleto:
                    itinerario_limpio = obtener_itinerario_limpio(boleto.ruta_vuelo)
                    descripcion = f"Boleto Aéreo: {itinerario_limpio}"
                    if boleto.numero_boleto:
                        descripcion += f" ({boleto.numero_boleto})"
                    descripcion = descripcion[:500]
                    nombre_pasajero = (
                        getattr(boleto, "nombre_pasajero_completo", "")
                        or getattr(boleto, "nombre_pasajero_procesado", "")
                        or ""
                    )
                    numero_boleto = boleto.numero_boleto or ""
                    itinerario = itinerario_limpio
                    codigo_aerolinea = (
                        boleto.proveedor_emisor.iata
                        if boleto.proveedor_emisor and boleto.proveedor_emisor.iata
                        else (boleto.aerolinea_emisora or "")
                    )[:10]
            else:
                tipo_servicio = ItemFactura.TipoServicio.ALOJAMIENTO_Y_OTROS_GRAVADOS

            es_gravado = item_venta.impuestos_item_venta > 0 or item_venta.tipo_item != "AIR"
            if es_gravado:
                tipo_impuesto = ItemFactura.TipoImpuesto.IVA_25
                alicuota_iva = Decimal("25.00")
            else:
                tipo_impuesto = ItemFactura.TipoImpuesto.EXENTO
                alicuota_iva = Decimal("0.00")

            ItemFactura.objects.create(
                agencia=factura.agencia,
                factura=factura,
                descripcion=descripcion,
                cantidad=item_venta.cantidad,
                precio_unitario=item_venta.precio_unitario_venta,
                tipo_servicio=tipo_servicio,
                es_gravado=es_gravado,
                tipo_impuesto=tipo_impuesto,
                alicuota_iva=alicuota_iva,
                nombre_pasajero=nombre_pasajero,
                numero_boleto=numero_boleto,
                itinerario=itinerario,
                codigo_aerolinea=codigo_aerolinea,
            )

        # 3. Recrear fee si existe
        total_fees = venta.fees_venta.aggregate(s=Sum("monto"))["s"] or Decimal("0.00")
        if total_fees > 0:
            ItemFactura.objects.create(
                agencia=factura.agencia,
                factura=factura,
                descripcion=f"Servicio de Gestión y Emisión - {venta.localizador or venta.pk}",
                cantidad=1,
                precio_unitario=total_fees,
                tipo_servicio=ItemFactura.TipoServicio.ALOJAMIENTO_Y_OTROS_GRAVADOS,
                es_gravado=True,
                tipo_impuesto=ItemFactura.TipoImpuesto.IVA_25,
                alicuota_iva=Decimal("25.00"),
            )

        # 4. Recalcular totales de la factura
        factura.calcular_impuestos_venezuela()

        # 5. Borrar el PDF obsoleto para que se regenere con los nuevos totales en la próxima descarga/vista
        if factura.archivo_pdf:
            try:
                factura.archivo_pdf.delete(save=False)
            except Exception as e:
                logger.error(f"Error borrando PDF obsoleto para factura {factura.pk}: {e}")
            factura.archivo_pdf = None
            factura.save(update_fields=["archivo_pdf"])

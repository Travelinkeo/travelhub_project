import datetime
import json
import logging

from django.db import transaction
from django.utils import timezone

from apps.automation.services.sales_intelligence_service import SalesIntelligenceService

# Modelos del Core
from apps.bookings.models import BoletoImportado, ItemVenta, ProductoServicio, Venta
from apps.bookings.services.itinerary_service import ItineraryService
from apps.common.services.customer_service import CustomerService

# SERVICIOS REFACTORIZADOS
from apps.finance.services.financial_engine import FinancialEngine

logger = logging.getLogger(__name__)


class VentaAutomationService:
    """VentaAutomationService."""

    @classmethod
    def crear_venta_desde_parser(
        cls,
        parsed_data,
        agencia,
        usuario=None,
        forced_cliente_id=None,
        proveedor_id=None,
        boleto_obj=None,
    ):
        """
        Crea o actualiza una venta calculando automáticamente la deuda con la Consolidadora.
        Refactorizado para usar servicios especializados (Audit Step 3).
        """
        # 0. Normalización de entrada
        data = parsed_data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception as e:
                logger.warning(f"No se pudo deserializar parsed_data como JSON: {e}")
                data = {}
        elif hasattr(data, "to_dict"):
            data = data.to_dict()
        elif not isinstance(data, dict):
            try:
                data = vars(data)
            except Exception as e:
                logger.warning(f"No se pudo convertir parsed_data a dict via vars(): {e}")
                data = {}

        # 1. Extracción Financiera (Refactorizado -> FinancialEngine)
        fin_data = FinancialEngine.calculate_ticket_amounts(data, boleto_obj)
        monto_base = fin_data["monto_base"]
        monto_total = fin_data["monto_total"]
        monto_impuestos = fin_data["monto_impuestos_total"]
        moneda_obj = fin_data["moneda_obj"]

        # 2. Cálculo de Comisiones y Márgenes (Refactorizado -> FinancialEngine)
        margin_data = FinancialEngine.calculate_margins(monto_total, data, proveedor_id)
        proveedor_obj = margin_data["proveedor_obj"]
        comision_monto = margin_data["comision_monto"]
        costo_neto_pagar = margin_data["costo_neto_pagar"]

        # 3. Guardado Atómico
        with transaction.atomic():
            # B. Datos de Identificación (🛡️ Audit Point 4: Exact Match)
            pnr = str(
                data.get("pnr")
                or data.get("CODIGO_RESERVA")
                or data.get("localizador")
                or "SIN-PNR"
            ).strip()
            ticket_num = str(
                data.get("ticket_number")
                or data.get("numero_boleto")
                or data.get("NUMERO_DE_BOLETO")
                or "SIN-TICKET"
            ).strip()

            aerolinea = data.get("nombre_aerolinea") or data.get("NOMBRE_AEROLINEA") or "Aéreo"

            # C. Venta (Cabecera)
            venta = None

            # Prioridad 1: Asociación Directa
            if boleto_obj and boleto_obj.venta_asociada:
                venta = boleto_obj.venta_asociada

            # Prioridad 2: Búsqueda por PNR (🛡️ Consolidación Multipasajero / Familias)
            if not venta and pnr != "SIN-PNR":
                manager = getattr(Venta, "all_objects", Venta.objects)
                venta_existente = (
                    manager.filter(agencia=agencia, localizador__iexact=pnr)
                    .order_by("-fecha_venta")
                    .first()
                )

                if venta_existente:
                    seis_meses = datetime.timedelta(days=180)
                    if (timezone.now() - venta_existente.fecha_venta) <= seis_meses:
                        venta = venta_existente
                        if hasattr(venta, "deleted_at") and venta.deleted_at:
                            venta.deleted_at = None
                            venta.save(update_fields=["deleted_at"])
                        logger.info(
                            f"🔗 Consolidando boleto {ticket_num} en Venta existente #{venta.pk} (PNR: {pnr})"
                        )

            # A. Cliente Titular
            if venta and venta.cliente:
                cliente = venta.cliente
            else:
                cliente = CustomerService.identify_or_create(data, agencia, forced_cliente_id)

            nombre_pax = f"{cliente.apellidos}, {cliente.nombres}" if cliente else "PASAJERO"

            if not venta:
                venta = Venta.objects.create(
                    agencia=agencia,
                    localizador=pnr,
                    cliente=cliente,
                    creado_por=usuario,
                    moneda=moneda_obj,
                    fecha_venta=timezone.now(),
                    estado=Venta.EstadoVenta.PENDIENTE_PAGO,
                    tipo_venta=Venta.TipoVenta.B2C,
                    canal_origen=Venta.CanalOrigen.IMPORTACION,
                    subtotal=monto_base,
                    impuestos=monto_impuestos,
                    total_venta=monto_total,
                    saldo_pendiente=monto_total,
                    descripcion_general=f"Emisión {aerolinea} - PNR: {pnr}",
                )
            else:
                if not venta.cliente and cliente:
                    venta.cliente = cliente
                venta.save()

            # D. Boleto Importado
            if not boleto_obj:
                boleto_obj = (
                    BoletoImportado.objects.filter(
                        agencia=agencia, numero_boleto__iexact=ticket_num
                    )
                    .order_by("-id_boleto_importado")
                    .first()
                )

                if not boleto_obj:
                    boleto_obj = BoletoImportado.objects.create(
                        agencia=agencia,
                        numero_boleto=ticket_num,
                        estado_parseo=BoletoImportado.EstadoParseo.COMPLETADO,
                    )

            boleto_obj.venta_asociada = venta
            boleto_obj.localizador_pnr = pnr
            boleto_obj.nombre_pasajero_procesado = nombre_pax
            boleto_obj.aerolinea_emisora = aerolinea
            boleto_obj.tarifa_base = monto_base
            boleto_obj.impuestos_total_calculado = monto_impuestos
            boleto_obj.total_boleto = monto_total
            boleto_obj.comision_agencia = comision_monto
            boleto_obj.datos_parseados = data
            boleto_obj.estado_parseo = BoletoImportado.EstadoParseo.COMPLETADO
            boleto_obj.save()

            producto_servicio, _ = ProductoServicio.all_objects.get_or_create(
                agencia=agencia,
                nombre="Boleto Aéreo Internacional",
                tipo_producto="AIR",
                defaults={
                    "descripcion": "Boleto aéreo importado/parseado automáticamente.",
                    "activo": True,
                    "codigo_interno": f"BOLETO_AIR_INT_{agencia.pk}"
                    if agencia
                    else "BOLETO_AIR_INT_GLOBAL",
                },
            )

            # 🛡️ EXACT MATCH para el item del boleto (evitar duplicados)
            # Buscamos por una descripción que contenga el número exacto del boleto
            item_existente = ItemVenta.all_objects.filter(
                venta=venta, descripcion_personalizada__contains=ticket_num
            ).first()

            item_data = {
                "agencia": agencia,
                "venta": venta,
                "producto_servicio": producto_servicio,
                "tipo_item": "AIR",
                "descripcion_personalizada": f"Boleto {ticket_num} ({aerolinea})",
                "cantidad": 1,
                "precio_unitario_venta": monto_base
                if (monto_base and monto_base > 0)
                else (
                    monto_total - monto_impuestos if monto_total >= monto_impuestos else monto_total
                ),
                "impuestos_item_venta": monto_impuestos,
                "proveedor_servicio": proveedor_obj,
                "costo_neto_proveedor": costo_neto_pagar,
                "comision_agencia_monto": comision_monto,
                "estado_item": ItemVenta.EstadoItemVenta.CONFIRMADO,
            }

            if item_existente:
                for key, value in item_data.items():
                    setattr(item_existente, key, value)
                item_existente.save()
                item_venta_obj = item_existente
            else:
                item_venta_obj = ItemVenta.objects.create(**item_data)

            # F. Pasajeros (Refactorizado -> CustomerService)
            CustomerService.sync_pasajero(data, agencia, venta)

            # G. Itinerario (Refactorizado -> ItineraryService)
            ItineraryService.sync_segments(data, agencia, venta, item_venta_obj, aerolinea)

            # H. Recalcular totales financieros acumulados de la Venta a partir de todos sus Items
            from decimal import Decimal

            from django.db.models import Sum

            item_mgr = getattr(ItemVenta, "all_objects", ItemVenta.objects)
            totals = item_mgr.filter(venta=venta).aggregate(
                total_subtotal=Sum("subtotal_item_venta"),
                total_impuestos=Sum("impuestos_item_venta"),
                total_total=Sum("total_item_venta"),
            )

            venta.subtotal = totals["total_subtotal"] or Decimal("0.00")
            venta.impuestos = totals["total_impuestos"] or Decimal("0.00")
            venta.total_venta = totals["total_total"] or Decimal("0.00")
            venta.saldo_pendiente = venta.total_venta - (venta.monto_pagado or Decimal("0"))

            if venta.estado == Venta.EstadoVenta.PAGADA_TOTAL and venta.saldo_pendiente > 0:
                if (venta.monto_pagado or Decimal("0")) > 0:
                    venta.estado = Venta.EstadoVenta.PAGADA_PARCIAL
                else:
                    venta.estado = Venta.EstadoVenta.PENDIENTE_PAGO
            elif (
                venta.estado == Venta.EstadoVenta.PENDIENTE_PAGO
                and (venta.monto_pagado or Decimal("0")) > 0
            ):
                if (venta.monto_pagado or Decimal("0")) >= venta.total_venta:
                    venta.estado = Venta.EstadoVenta.PAGADA_TOTAL
                else:
                    venta.estado = Venta.EstadoVenta.PAGADA_PARCIAL

            # Actualizar también descripción general para listar múltiples pasajeros si los hay
            pax_names = []
            for p in venta.pasajeros.all():
                pax_names.append(f"{p.apellidos}, {p.nombres}")
            venta.save()

            # I. Auto-Deducción de Saldo de Billetera (Titular o Dependientes)
            try:
                from apps.crm.services.wallet_service import WalletClienteService

                WalletClienteService.aplicar_saldo_automatico_a_venta(venta, usuario=usuario)
            except Exception as e_wallet:
                logger.warning(
                    f"No se pudo auto-descontar saldo de billetera para Venta #{venta.pk}: {e_wallet}"
                )

        # H. Sales Intelligence (Audit Point 7) - FUERA de la transacción
        try:
            ai_report = SalesIntelligenceService.analyze_booking_for_upselling(
                data, agencia=agencia
            )
            if ai_report:
                formatted_report = SalesIntelligenceService.format_report_for_display(ai_report)
                if formatted_report and formatted_report.strip():
                    manual_notes = venta.notas_manuales or ""
                    if manual_notes:
                        venta.notas = f"{manual_notes}\n\n[IA SALES REPORT]\n{formatted_report}"
                    else:
                        venta.notas = f"[IA SALES REPORT]\n{formatted_report}"
                    venta.save(update_fields=["notas"])
        except Exception as ei:
            logger.error(f"Error generando inteligencia de ventas: {ei}")

        return venta

import logging
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from apps.bookings.models.servicios import ProductoServicio
from apps.bookings.models.venta import ItemVenta, Venta
from apps.common.models import Moneda
from apps.crm.models import Pasajero

logger = logging.getLogger(__name__)


class VentaAutomationService:
    """
    Servicio centralizado para la automatización de lógica de negocio
    tras la importación de boletos y otros componentes.
    Desacoplado de signals.py para mejorar testabilidad y escalabilidad.
    """

    @staticmethod
    def process_ticket_import(instance):
        """
        Crea Venta, Pasajero e Items a partir de un BoletoImportado.
        """
        data = instance.datos_parseados
        if not data:
            return None

        # --- Extracción de Campos ---
        pax_data = data.get("passenger", {})
        pasajero_nombre_completo = pax_data.get("name") or data.get("PASAJERO")
        numero_documento = pax_data.get("customerNumber") or data.get("ID_PASAJERO")

        booking_data = data.get("bookingDetails", {})
        localizador = (
            booking_data.get("reservationCode")
            or data.get("LOCALIZADOR")
            or data.get("RECORD_LOCATOR")
        )

        moneda_iso = data.get("moneda") or data.get("CURRENCY") or "USD"
        total_str = data.get("total") or data.get("TOTAL_BOLETO") or "0.00"
        aerolinea = booking_data.get("issuingAirline") or data.get("AEROLINEA") or "Desconocida"

        if not localizador:
            logger.warning(
                f"⚠️ Boleto {instance.pk} sin localizador. No se puede automatizar venta."
            )
            return None

        try:
            # --- 1. Aislamiento de Agencia ---
            agencia_owner = instance.agencia
            if not agencia_owner:
                logger.error(f"🚫 CRÍTICO: BoletoImportado {instance.pk} sin agencia. ABORTANDO.")
                return None

            # --- 2. Gestión de Pasajero ---
            nombres, apellidos = "", ""
            if pasajero_nombre_completo:
                parts = pasajero_nombre_completo.split("/")
                if len(parts) > 1:
                    apellidos, nombres = parts[0].strip(), parts[1].strip()
                else:
                    apellidos = pasajero_nombre_completo.strip()

            nombres = (nombres or "PASAJERO")[:100]
            apellidos = (apellidos or "SIN NOMBRE")[:100]

            if not numero_documento:
                # Fallback determinístico para evitar duplicados si no hay ID
                numero_documento = (
                    f"TMP-{apellidos.replace(' ', '')}-{nombres.replace(' ', '')}".upper()
                )

            pasajero, _ = Pasajero.objects.get_or_create(
                numero_documento=numero_documento,
                agencia=agencia_owner,
                defaults={
                    "nombres": nombres,
                    "apellidos": apellidos,
                },
            )

            # --- 3. Gestión de Moneda ---
            moneda_codigo = str(moneda_iso).upper()[:3]
            moneda = Moneda.objects.filter(codigo_iso=moneda_codigo).first()
            if not moneda:
                moneda, _ = Moneda.objects.get_or_create(
                    codigo_iso="USD", defaults={"nombre": "Dólar"}
                )

            # --- 4. Gestión de Venta (Atómica) ---
            venta, _ = Venta.objects.get_or_create(
                localizador=localizador,
                agencia=agencia_owner,
                defaults={
                    "moneda": moneda,
                    "canal_origen": Venta.CanalOrigen.IMPORTACION,
                    "descripcion_general": f"Venta automatizada desde PNR {localizador}",
                },
            )

            venta.pasajeros.add(pasajero)

            producto_boleto, _ = ProductoServicio.objects.get_or_create(
                nombre="Boleto Aéreo",
                defaults={
                    "tipo_producto": "SER",
                    "agencia": agencia_owner,
                    "codigo_interno": f"BOLETO_AEREO_{agencia_owner.pk}"
                    if agencia_owner
                    else "BOLETO_AEREO_GLOBAL",
                },
            )

            # Limpieza robusta de total
            try:
                clean_total = str(total_str).replace(",", "").replace(" ", "").replace("$", "")
                total_boleto = Decimal(clean_total)
            except (ValueError, InvalidOperation):
                total_boleto = Decimal("0.00")

            ItemVenta.objects.get_or_create(
                venta=venta,
                agencia=agencia_owner,
                producto_servicio=producto_boleto,
                precio_unitario_venta=total_boleto,
                defaults={
                    "descripcion_personalizada": f"Boleto {aerolinea} - {pasajero.get_nombre_completo()}",
                    "cantidad": 1,
                },
            )

            # Recalculate totals
            from django.db.models import Sum

            totals = ItemVenta.objects.filter(venta=venta).aggregate(
                total_subtotal=Sum("subtotal_item_venta"),
                total_impuestos=Sum("impuestos_item_venta"),
                total_total=Sum("total_item_venta"),
            )
            venta.subtotal = totals["total_subtotal"] or Decimal("0.00")
            venta.impuestos = totals["total_impuestos"] or Decimal("0.00")
            venta.total_venta = totals["total_total"] or Decimal("0.00")
            venta.saldo_pendiente = venta.total_venta - (venta.monto_pagado or Decimal("0.00"))
            venta.save()

            # --- 6. Vinculación Final ---
            instance.venta_asociada = venta
            instance.save(update_fields=["venta_asociada"])

            logger.info(f"✅ Automatización exitosa: Venta {venta.localizador}")

            # --- 7. Validación Migratoria (Opcional) ---
            try:
                from django.utils.module_loading import import_string

                MigrationCheckerService = import_string(
                    "apps.automation.services.migration_checker_service.MigrationCheckerService"
                )
                mig_service = MigrationCheckerService()

                flights_data = []
                flights_raw = data.get("flights", [])
                if not flights_raw and "itinerary" in data:  # Fallback legacy
                    flights_raw = data.get("itinerary", [])

                for f in flights_raw:
                    dep = f.get("departure", {})
                    arr = f.get("arrival", {})
                    flights_data.append(
                        {
                            "origen": (dep.get("location") or dep.get("city") or "")[:3].upper(),
                            "destino": (arr.get("location") or arr.get("city") or "")[:3].upper(),
                            "fecha": f.get("date") or timezone.now().date().isoformat(),
                        }
                    )

                if flights_data:
                    mig_service.check_migration_requirements(
                        pasajero_id=pasajero.id_pasajero,
                        vuelos=flights_data,
                        venta_id=venta.id_venta,
                    )
            except Exception as e_mig:
                logger.error(f"⚠️ Error migratorio: {e_mig}")

            return venta

        except Exception as e:
            logger.exception(f"❌ Error crítico en process_ticket_import: {str(e)}")
            return None

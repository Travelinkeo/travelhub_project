import logging

from django.db import transaction

from apps.bookings.models import BoletoImportado, Proveedor
from apps.common.models import Aerolinea

# SERVICIOS

logger = logging.getLogger(__name__)


class BoletoPersistenceService:
    """
    🎯 Responsabilidad: Guardar y versionar registros de BoletoImportado en la DB.
    """

    @staticmethod
    @transaction.atomic
    def update_boleto_from_data(boleto, data):
        """Actualiza los campos del modelo BoletoImportado con la data normalizada."""
        try:
            # 🛡️ FIX SEGURIDAD: Si data es un string (JSON), lo parseamos
            import json

            d = data
            if isinstance(d, str):
                try:
                    d = json.loads(d)
                except Exception as e:
                    logger.warning(f"No se pudo parsear data como JSON en update_boleto: {e}")
                    d = {}

            if not isinstance(d, dict):
                d = {}

            # 1. Identificación básica
            boleto.localizador_pnr = BoletoPersistenceService._truncate(d.get("pnr"), 20)
            boleto.numero_boleto = BoletoPersistenceService._truncate(d.get("ticket_number"), 50)

            # 2. Pasajero
            p_name = d.get("passenger_name_original") or d.get("passenger_name")
            if p_name:
                p_name = str(p_name).split(" FOID")[0].split(" RIF")[0].strip()
            boleto.nombre_pasajero_completo = BoletoPersistenceService._truncate(p_name, 150)
            boleto.nombre_pasajero_procesado = BoletoPersistenceService._truncate(
                d.get("SOLO_NOMBRE_PASAJERO") or d.get("solo_nombre_pasajero") or p_name, 150
            )
            boleto.foid_pasajero = BoletoPersistenceService._truncate(
                d.get("passenger_document"), 50
            )

            # 3. Aerolínea y Proveedor
            boleto.aerolinea_emisora = BoletoPersistenceService._truncate(
                d.get("issuing_airline"), 150
            )
            iata_code = d.get("agencia_iata") or d.get("agency_iata")

            if not iata_code and boleto.aerolinea_emisora:
                aero_obj = Aerolinea.objects.filter(
                    nombre__icontains=boleto.aerolinea_emisora
                ).first()
                if aero_obj:
                    iata_code = aero_obj.codigo_iata

            office_id = d.get("office_id")
            boleto.proveedor_emisor = BoletoPersistenceService._find_provider(iata_code, office_id)

            # 4. Financiero (Audit Step 3.2: Centralización en FinancialEngine)
            from apps.finance.services.financial_engine import FinancialEngine

            fin_data = FinancialEngine.calculate_ticket_amounts(d, boleto)

            boleto.total_boleto = fin_data["monto_total"]
            boleto.tarifa_base = fin_data["monto_base"]
            boleto.iva_monto = fin_data["monto_iva_yn"]
            boleto.inatur_monto = fin_data["monto_inatur"]
            boleto.otros_impuestos_monto = fin_data["monto_otros_tax"]
            boleto.impuestos_total_calculado = fin_data["monto_impuestos_total"]

            # 5. Metadatos y Moneda
            boleto.moneda = fin_data["moneda_obj"]

            boleto.ruta_vuelo = d.get("ItinerarioFinalLimpio")
            boleto.datos_parseados = d

            # Fecha de emisión
            fecha_str = d.get("issue_date")
            if fecha_str:
                from apps.automation.parsers.ticket_parser import _parse_date_robust

                boleto.fecha_emision_boleto = _parse_date_robust(fecha_str)

            boleto.save()
            return boleto
        except Exception as e:
            logger.error(f"Error en BoletoPersistenceService: {e}", exc_info=True)
            raise

    @staticmethod
    def handle_versioning(boleto):
        """Gestiona versiones de re-emisión si el número de boleto ya existe."""
        if not boleto.numero_boleto:
            return

        duplicados = (
            BoletoImportado.objects.filter(numero_boleto=boleto.numero_boleto)
            .exclude(pk=boleto.pk)
            .order_by("-version")
        )

        ultimo = duplicados.first()
        if ultimo:
            # Si el boleto anterior fue anulado (VOID), no es una re-emisión legítima
            is_anulado = (
                getattr(ultimo, "estado_emision", None) == BoletoImportado.EstadoEmision.ANULADO
            )
            if not is_anulado:
                boleto.version = ultimo.version + 1
                boleto.boleto_padre = ultimo
                boleto.estado_emision = BoletoImportado.EstadoEmision.REEMISION
                boleto.save(update_fields=["version", "boleto_padre", "estado_emision"])

    @staticmethod
    def _truncate(val, max_len):
        if not val:
            return None
        s = str(val).strip()
        return s[:max_len]

    @staticmethod
    def _find_provider(iata, office_id):
        if not iata and not office_id:
            return None
        try:
            candidatos = Proveedor.objects.filter(identificadores_gds__isnull=False)
            for prov in candidatos:
                gds_ids = prov.identificadores_gds
                if not isinstance(gds_ids, dict):
                    continue
                if iata and iata in gds_ids.get("IATA", []):
                    return prov
                if office_id and office_id in gds_ids.get("OFFICE_ID", []):
                    return prov
        except Exception as e:
            logger.warning(f"No se pudo buscar proveedor por IATA/OfficeID: {e}")
        return None

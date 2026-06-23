import json
import logging
from datetime import date, datetime
from decimal import Decimal

from apps.common.utils import clean_currency

logger = logging.getLogger(__name__)


class DataNormalizationService:
    """
    🎯 Responsabilidad: Normalizar datos extraídos por diversos motores (Regex/IA) a un esquema unificado.
    """

    @staticmethod
    def normalize_ticket_data(data):
        """Aplica alias y limpieza de campos para compatibilidad con el motor financiero."""
        # 🛡️ FIX SEGURIDAD: Si data es un string (JSON), lo parseamos
        d = data
        if isinstance(d, str):
            try:
                d = json.loads(d)
            except Exception as e:
                logger.warning(f"No se pudo parsear datos como JSON: {e}")
                d = {}

        if not isinstance(d, dict):
            return d or {}

        data = d  # Trabajamos con el dict parseado

        # 1. Aliasing de campos comunes
        mappings = {
            "pnr": ["codigo_reserva", "localizador", "CODIGO_RESERVA", "codigo_reservacion"],
            "reservation_code": [
                "pnr",
                "codigo_reserva",
                "localizador",
                "CODIGO_RESERVA",
                "codigo_reservacion",
            ],
            "passenger_name": [
                "nombre_pasajero",
                "NOMBRE_DEL_PASAJERO",
                "nombre_completo",
                "passenger name",
                "preparado_para",
            ],
            "ticket_number": ["numero_boleto", "NUMERO_DE_BOLETO"],
            "issue_date": ["FECHA_DE_EMISION", "fecha_emision", "fecha_emision_iso"],
            "issuing_airline": [
                "NOMBRE_AEROLINEA",
                "nombre_aerolinea",
                "aerolinea_emisora",
                "airline",
                "airline_name",
            ],
            "airline_name": [
                "issuing_airline",
                "NOMBRE_AEROLINEA",
                "nombre_aerolinea",
                "aerolinea_emisora",
                "airline",
            ],
            "passenger_document": [
                "CODIGO_IDENTIFICACION",
                "codigo_identificación",
                "foid",
                "passenger_id",
                "documento_identidad",
            ],
            "fare_amount": ["tarifa", "TARIFA_IMPORTE"],
            "total_amount": ["total", "TOTAL", "TOTAL_IMPORTE"],
            "total_currency": ["moneda", "TOTAL_MONEDA", "currency"],
            "airline_pnr": [
                "pnr_aerolinea",
                "CODIGO_RESERVA_AEROLINEA",
                "airline_reservation_code",
            ],
        }

        normalized = data.copy()
        for target, sources in mappings.items():
            if target not in normalized or not normalized[target]:
                for source in sources:
                    if source in normalized and normalized[source]:
                        normalized[target] = normalized[source]
                        break

        # 1.0 Normalización de Aerolínea (Uso de catálogo centralizado)
        try:
            from apps.automation.parsers.airline_utils import normalize_airline_name

            raw_aero = normalized.get("issuing_airline")
            vuelo_ref = None
            # Intentar obtener el primer vuelo para ayudar a la normalización
            if "segmentos" in normalized and normalized["segmentos"]:
                vuelo_ref = normalized["segmentos"][0].get("vuelo")
            elif (
                "itinerario" in normalized
                and normalized["itinerario"]
                and isinstance(normalized["itinerario"], list)
            ):
                vuelo_ref = normalized["itinerario"][0].get("vuelo")

            normalized["issuing_airline"] = normalize_airline_name(
                raw_aero, flight_number=vuelo_ref, ticket_number=normalized.get("ticket_number")
            )
            # Actualizar también los alias para consistencia
            normalized["aerolinea_emisora"] = normalized["issuing_airline"]
            normalized["nombre_aerolinea"] = normalized["issuing_airline"]
        except Exception as e:
            logger.error(f"Error normalizando aerolínea en pipeline: {e}")

        # 1.1 Normalización específica de nombre de pasajero (Hola, [Nombre])
        raw_name = normalized.get("passenger_name", "")
        if raw_name:
            import re

            try:
                if "/" in raw_name:
                    # GDS Standard: APELLIDOS/NOMBRES MR
                    parts = raw_name.split("/")
                    if len(parts) > 1:
                        last_names = parts[0].strip()
                        first_names_raw = parts[1].strip()
                        first_names = re.sub(
                            r"\s+(MR|MRS|MS|MSTR|MISS|M|F)$",
                            "",
                            first_names_raw,
                            flags=re.IGNORECASE,
                        )
                        normalized["first_name"] = first_names
                        normalized["last_name"] = last_names
                        normalized["solo_nombre_pasajero"] = first_names.split(" ")[0]
                        normalized["human_name"] = f"{first_names} {last_names}"
                        normalized["passenger_name_original"] = raw_name
                        normalized["passenger_name"] = normalized["human_name"]
                else:
                    # Fallback: NOMBRE APELLIDO (separado por espacio)
                    parts = raw_name.strip().split(None, 1)
                    if len(parts) > 1:
                        first_names = parts[0].strip()
                        last_names = parts[1].strip()
                    else:
                        first_names = parts[0].strip()
                        last_names = ""
                    first_names = re.sub(
                        r"\s+(MR|MRS|MS|MSTR|MISS|M|F)$", "", first_names, flags=re.IGNORECASE
                    )
                    normalized["first_name"] = first_names
                    normalized["last_name"] = last_names
                    normalized["solo_nombre_pasajero"] = first_names.split(" ")[0]
                    normalized["human_name"] = f"{first_names} {last_names}".strip()
                    normalized["passenger_name_original"] = raw_name
                    normalized["passenger_name"] = normalized["human_name"]
            except Exception as e:
                logger.error(f"Error normalizando nombre {raw_name}: {e}")

        # 2. Procesamiento de Itinerario
        if (
            "itinerario" in normalized
            or "flights" in normalized
            or "segmentos" in normalized
            or "vuelos" in normalized
        ):
            raw_itinerary = (
                normalized.get("itinerario")
                or normalized.get("flights")
                or normalized.get("segmentos")
                or normalized.get("vuelos")
                or []
            )
            normalized["segmentos"] = DataNormalizationService._normalize_itinerary(raw_itinerary)
            # Para compatibilidad con legacy
            normalized["ItinerarioFinalLimpio"] = json.dumps(raw_itinerary)

        return DataNormalizationService.sanitize_for_json(normalized)

    @staticmethod
    def _normalize_itinerary(raw_itinerary):
        segmentos = []
        from apps.common.services.catalog_service import CatalogNormalizationService

        for tramo in raw_itinerary:
            if not isinstance(tramo, dict):
                continue

            # Soporte para estructura anidada (Gemini) vs plana (Regex)
            dep = tramo.get("departure", {}) if isinstance(tramo.get("departure"), dict) else {}
            arr = tramo.get("arrival", {}) if isinstance(tramo.get("arrival"), dict) else {}
            det = tramo.get("details", {}) if isinstance(tramo.get("details"), dict) else {}

            vuelo_num = tramo.get("flightNumber") or tramo.get("numero_vuelo") or tramo.get("vuelo")

            # Normalización de tiempos
            h_salida = DataNormalizationService._normalize_time(
                dep.get("time") or tramo.get("hora_salida")
            )
            h_llegada = DataNormalizationService._normalize_time(
                arr.get("time") or tramo.get("hora_llegada")
            )

            # --- 🏙️ NORMALIZACIÓN POR CATÁLOGO IATA (DETERMINÍSTICO) ---
            origen_raw = dep.get("location") or tramo.get("origen")
            if isinstance(origen_raw, dict):
                origen_raw = origen_raw.get("ciudad") or origen_raw.get("city") or ""
            iata_origen = tramo.get("codigo_iata_origen") or (
                origen_raw if len(str(origen_raw)) == 3 else None
            )

            destino_raw = arr.get("location") or tramo.get("destino")
            if isinstance(destino_raw, dict):
                destino_raw = destino_raw.get("ciudad") or destino_raw.get("city") or ""
            iata_destino = tramo.get("codigo_iata_destino") or (
                destino_raw if len(str(destino_raw)) == 3 else None
            )

            # Resolver nombres vía catálogo si tenemos IATA
            ciudad_origen_obj = (
                CatalogNormalizationService.get_or_create_ciudad_by_iata(iata_origen)
                if iata_origen
                else None
            )
            ciudad_destino_obj = (
                CatalogNormalizationService.get_or_create_ciudad_by_iata(iata_destino)
                if iata_destino
                else None
            )

            segmento = {
                "aerolinea": tramo.get("airline") or tramo.get("aerolinea"),
                "vuelo": vuelo_num,
                "numero_vuelo": vuelo_num,
                "origen": ciudad_origen_obj.nombre if ciudad_origen_obj else origen_raw,
                "codigo_iata_origen": iata_origen,
                "destino": ciudad_destino_obj.nombre if ciudad_destino_obj else destino_raw,
                "codigo_iata_destino": iata_destino,
                "fecha_salida": dep.get("date") or tramo.get("fecha_salida") or tramo.get("date"),
                "hora_salida": h_salida,
                "fecha_llegada": arr.get("date") or tramo.get("fecha_llegada"),
                "hora_llegada": h_llegada,
                "clase": det.get("cabin") or tramo.get("clase") or tramo.get("cabina") or "Y",
                "localizador_aerolinea": det.get("airlineReservationCode")
                or tramo.get("localizador_aerolinea")
                or tramo.get("airline_pnr")
                or tramo.get("pnr_aerolinea"),
            }
            segmentos.append(segmento)
        return segmentos

    @staticmethod
    def _normalize_time(time_str):
        """Normaliza horas a formato 24h HH:mm"""
        if not time_str:
            return None
        s = str(time_str).strip().upper()

        # 1. Quitar segundos si existen (17:00:00 -> 17:00)
        s = s.split(":")[0] + ":" + s.split(":")[1] if len(s.split(":")) > 2 else s

        # 2. Conversión AM/PM
        if "AM" in s or "PM" in s:
            try:
                # Limpiar ruidos
                s_clean = s.replace("AM", " AM").replace("PM", " PM").replace("  ", " ")
                from datetime import datetime

                dt = datetime.strptime(s_clean, "%I:%M %p")
                return dt.strftime("%H:%M")
            except Exception as e:
                logger.warning(f"No se pudo convertir tiempo '{time_str}' a formato 24h: {e}")

        # 3. Formato GDS (1721 -> 17:21)
        if len(s) == 4 and s.isdigit():
            return f"{s[:2]}:{s[2:]}"

        return s

    @staticmethod
    def sanitize_for_json(data):
        if isinstance(data, dict):
            return {k: DataNormalizationService.sanitize_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [DataNormalizationService.sanitize_for_json(v) for v in data]
        elif isinstance(data, date | datetime):
            return data.isoformat()
        elif isinstance(data, Decimal):
            return str(data)
        return data

    @staticmethod
    def safe_decimal(val):
        return clean_currency(val)

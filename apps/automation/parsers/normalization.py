import json
import logging
from datetime import date, datetime
from decimal import Decimal

from apps.common.utils import clean_currency

logger = logging.getLogger(__name__)

# --- MAPAS CENTRALIZADOS DE MESES GDS (S2-A) ---
GDS_MONTH_EN = {
    "ENE": "JAN",
    "FEB": "FEB",
    "MAR": "MAR",
    "ABR": "APR",
    "MAY": "MAY",
    "JUN": "JUN",
    "JUL": "JUL",
    "AGO": "AUG",
    "SEP": "SEP",
    "OCT": "OCT",
    "NOV": "NOV",
    "DIC": "DEC",
}

GDS_MONTH_ES = {
    "enero": "ENE",
    "febrero": "FEB",
    "marzo": "MAR",
    "abril": "ABR",
    "mayo": "MAY",
    "junio": "JUN",
    "julio": "JUL",
    "agosto": "AGO",
    "septiembre": "SEP",
    "octubre": "OCT",
    "noviembre": "NOV",
    "diciembre": "DIC",
}

GDS_MONTH_NUM = {
    1: "ENE",
    2: "FEB",
    3: "MAR",
    4: "ABR",
    5: "MAY",
    6: "JUN",
    7: "JUL",
    8: "AGO",
    9: "SEP",
    10: "OCT",
    11: "NOV",
    12: "DIC",
}

GDS_NUM_TO_EN = {
    1: "JAN",
    2: "FEB",
    3: "MAR",
    4: "APR",
    5: "MAY",
    6: "JUN",
    7: "JUL",
    8: "AUG",
    9: "SEP",
    10: "OCT",
    11: "NOV",
    12: "DEC",
}

# Alias para compatibilidad con el plan de remediación original
GDS_MONTH_MAP = GDS_MONTH_ES

GDS_SHORT_TO_NUM = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
    "ENE": 1,
    "ABR": 4,
    "AGO": 8,
    "DIC": 12,
}


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
                "localizador_aerolinea",
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
            default_airline_pnr = (
                normalized.get("airline_pnr")
                or normalized.get("localizador_aerolinea")
                or normalized.get("pnr_aerolinea")
            )
            normalized["segmentos"] = DataNormalizationService._normalize_itinerary(
                raw_itinerary, default_airline_pnr=default_airline_pnr
            )
            # Para compatibilidad con legacy
            normalized["ItinerarioFinalLimpio"] = json.dumps(raw_itinerary)

        return DataNormalizationService.sanitize_for_json(normalized)

    @staticmethod
    def _normalize_itinerary(raw_itinerary, default_airline_pnr=None):
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

            # 🏙️ Búsqueda inversa de IATA por nombre de ciudad si no se tiene el código de 3 letras.
            # IMPORTANTE: varios GDS (KIU/Turpial, Estelar) imprimen el NOMBRE de ciudad en
            # la columna FROM/TO en lugar del código IATA — particularmente para rutas
            # domésticas Venezolanas. Antes iterábamos 29.305 aeropuertos por tramo y
            # menudo tomábamos el primero ambiguo (ej: "San Antonio" → Texas/US en vez de
            # San Antonio del Táchira/SVZ). Ahora usamos:
            #   1. Alias manuales por nombre (LatAm/Venezuela) → O(1).
            #   2. Índice city→[aeropuertos] precomputado → O(1) + desempate por país.
            #   3. Si hay múltiples candidatos sin desempate claro, NO inventamos IATA
            #      (preferimos dejar el nombre limpio a poner un IATA equivocado que
            #      ensucie la venta y el PDF).
            iata_origen = DataNormalizationService._resolve_iata_from_city(
                origen_raw,
                current_iata=iata_origen,
            )
            iata_destino = DataNormalizationService._resolve_iata_from_city(
                destino_raw,
                current_iata=iata_destino,
            )

            # Resolver nombres vía catálogo si tenemos IATA
            try:
                ciudad_origen_obj = (
                    CatalogNormalizationService.get_or_create_ciudad_by_iata(iata_origen)
                    if iata_origen
                    else None
                )
            except Exception as e_city_o:
                logger.warning(
                    f"⚠️ _normalize_itinerary: fallo resolviendo ciudad origen "
                    f"(iata={iata_origen}, raw={origen_raw!r}): {e_city_o}. Continuando sin ciudad."
                )
                ciudad_origen_obj = None
            try:
                ciudad_destino_obj = (
                    CatalogNormalizationService.get_or_create_ciudad_by_iata(iata_destino)
                    if iata_destino
                    else None
                )
            except Exception as e_city_d:
                logger.warning(
                    f"⚠️ _normalize_itinerary: fallo resolviendo ciudad destino "
                    f"(iata={iata_destino}, raw={destino_raw!r}): {e_city_d}. Continuando sin ciudad."
                )
                ciudad_destino_obj = None

            segmento = {
                "aerolinea": tramo.get("airline") or tramo.get("aerolinea"),
                "vuelo": vuelo_num,
                "numero_vuelo": vuelo_num,
                "origen": (
                    ciudad_origen_obj.nombre.upper()
                    if (ciudad_origen_obj and ciudad_origen_obj.nombre)
                    else str(origen_raw or "").upper()
                ),
                "codigo_iata_origen": iata_origen,
                "destino": (
                    ciudad_destino_obj.nombre.upper()
                    if (ciudad_destino_obj and ciudad_destino_obj.nombre)
                    else str(destino_raw or "").upper()
                ),
                "codigo_iata_destino": iata_destino,
                "fecha_salida": dep.get("date") or tramo.get("fecha_salida") or tramo.get("date"),
                "hora_salida": h_salida,
                "fecha_llegada": arr.get("date") or tramo.get("fecha_llegada"),
                "hora_llegada": h_llegada,
                "clase": det.get("cabin") or tramo.get("clase") or tramo.get("cabina") or "Y",
                "localizador_aerolinea": det.get("airlineReservationCode")
                or tramo.get("localizador_aerolinea")
                or tramo.get("airline_pnr")
                or tramo.get("pnr_aerolinea")
                or default_airline_pnr,
            }
            segmentos.append(segmento)
        return segmentos

    @staticmethod
    def _resolve_iata_from_city(raw_value, current_iata: str | None = None) -> str | None:
        """
        Resuelve el código IATA de 3 letras a partir de un valor crudo (puede ser
        nombre de ciudad, código IATA, o una cadena compuesta "CIUDAD, PAIS").

        Estrategia (en orden, primera que gana):
          0. Si `current_iata` ya viene seteado desde el parser, respetarlo.
          1. Si el valor crudo ya es IATA de 3 letras, usarlo tras validarlo contra
             el índice O(1) del airports_master.
          2. Alias manuales LatAm/Venezuela (CITY_NAME_ALIASES) — el GDS KIU/Turpial
             imprime el NOMBRE de ciudad en la columna FROM/TO para rutas domésticas.
          3. Índice city→[aeropuertos] del maestro:
             - Si hay 1 candidato, usarlo.
             - Si hay múltiples, intentar desempate por país/name si están en el raw.
             - Si no hay desempate claro, NO inventar IATA (devolver current_iata
               o None) — preferimos dejar el nombre bien a tener un IATA equivocado
               que contamine la venta/PDF/búsqueda.
          4. Como último recurso, devolver current_iata (None por defecto).

        Esto reemplaza el loop O(N) anterior que iteraba 29.305 aeropuertos por tramo.
        """
        if current_iata:
            return current_iata
        if not raw_value:
            return None

        raw_str = str(raw_value).strip()
        raw_upper = raw_str.upper()
        # Limpiar el componente país (ej: "VALENCIA, VENEZUELA")
        clean_city = raw_upper.split(",")[0].strip()
        # Quitar sufijo de estado de 2 letras (ej: "SAN ANTONIO TX" -> "SAN ANTONIO")
        words = clean_city.split()
        if words and len(words[-1]) == 2 and words[-1].isalpha() and len(words) > 1:
            clean_city = " ".join(words[:-1])

        # 1. ¿El valor crudo ya es IATA de 3 letras?
        if len(raw_str) == 3 and raw_str.isalpha():
            from apps.common.services.catalog_service import CatalogNormalizationService

            if CatalogNormalizationService._get_airports_by_iata(raw_upper):
                return raw_upper
            # Aunque no esté en el maestro, podría existir en DB (RLS/contexto).
            # Lo dejamos pasar: la get_or_create lo validará contra DB.
            return raw_upper

        # 2. Alias manuales (alta prioridad para LatAm/Venezuela doméstica)
        from apps.common.services.catalog_service import CatalogNormalizationService

        alias_iata = CatalogNormalizationService.CITY_NAME_ALIASES.get(clean_city)
        if alias_iata:
            # Validar que existe en el maestro o en DB (si no, igual lo dejamos,
            # get_or_create_ciudad_by_iata lo resolverá).
            return alias_iata

        # 3. Índice city→[aeropuertos] (O(1))
        candidatos = CatalogNormalizationService._get_airports_by_city(clean_city)
        if not candidatos:
            return None

        # Filtrar sólo los que tengan un IATA de 3 letras válido
        candidatos_validos = []
        for info in candidatos:
            iata_val = (info.get("iata") or "").strip().upper()
            if iata_val and len(iata_val) == 3:
                candidatos_validos.append((iata_val, info))

        if not candidatos_validos:
            return None
        if len(candidatos_validos) == 1:
            return candidatos_validos[0][0]

        # Desempate por país o nombre del aeropuerto que aparezca en el raw_upper
        raw_with_country = raw_upper
        for iata_val, info in candidatos_validos:
            country = (info.get("country") or "").upper()
            airport_name = (info.get("name") or "").upper()
            state = (info.get("state") or "").upper()
            if (
                (country and country in raw_with_country)
                or (airport_name and airport_name in raw_with_country)
                or (state and state in raw_with_country)
            ):
                return iata_val

        # No hay desempate confiable. NO inventar: devolver None para que el
        # segmento se quede con el nombre limpio (no con un IATA ambiguo/equivocado).
        logger.info(
            f"ℹ️ _resolve_iata_from_city: ciudad ambigua '{clean_city}' con "
            f"{len(candidatos_validos)} IATA candidatos — manteniendo None para evitar mapeo erróneo."
        )
        return None

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

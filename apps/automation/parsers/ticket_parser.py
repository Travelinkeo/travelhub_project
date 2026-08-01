import hashlib
import logging
import re
from typing import Any

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Prefijos IATA numéricos de aerolínea (los 3 primeros dígitos del boleto).
# Solo se incluyen códigos verificados; si la aerolínea no está en el mapa,
# NO se fabrica un prefijo (evita corromper números de boleto).
AIRLINE_IATA_CODES = {
    "TURKISH AIRLINES": "235",
    "COPA AIRLINES": "230",
    "AVIANCA": "134",
    "IBERIA": "075",
    "LATAM AIRLINES": "045",
    "AIR EUROPA": "096",
    "TAP AIR PORTUGAL": "047",
    "AMERICAN AIRLINES": "001",
}

# Orden de detección: las más específicas primero para evitar falsos positivos.
_AIRLINE_RULES = [
    ("TURKISH AIRLINES", ("TURKISH",)),
    ("LASER AIRLINES", ("LASER",)),
    ("COPA AIRLINES", ("COPA",)),
    ("AVIANCA", ("AVIANCA", "AEROVIAS DEL CONTINENTE")),
    ("IBERIA", ("IBERIA",)),
    ("LATAM AIRLINES", ("LATAM",)),
    ("AIR EUROPA", ("AIR EUROPA",)),
    ("CONVIASA", ("CONVIASA",)),
    ("RUTACA AIRLINES", ("RUTACA",)),
    ("AEROVÍAS ESTELAR", ("ESTELAR",)),
    ("FLYBONDI", ("FLYBONDI",)),
    ("JETSMART", ("JETSMART",)),
    ("SKY AIRLINE", ("SKY AIRLINE", "SKYAIRLINE")),
    ("TAP AIR PORTUGAL", ("TAP PORTUGAL", "TAP AIR")),
    ("TURPIAL AIRLINES", ("TURPIAL",)),
    (
        "AMERICAN AIRLINES",
        ("AMERICAN AIRLINES", "AMERICAN"),
    ),
]


def _detect_airline(text_upper: str) -> str | None:
    """Devuelve el nombre de la aerolínea detectada o None."""
    for name, keywords in _AIRLINE_RULES:
        if any(k in text_upper for k in keywords):
            return name
    return None


# Importar métricas
try:
    from apps.automation.metrics.parser_metrics import track_parser_execution

    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False

    def track_parser_execution(parser_type: str, feature: str = "generic"):
        def decorator(func):
            return func

        return decorator


def _get_solo_nombre_pasajero(nombre_completo: str) -> str:
    """Extrae el nombre (o nombres) de un formato APELLIDO/NOMBRE o similar, eliminando títulos de cortesía."""
    if not nombre_completo or nombre_completo == "No encontrado":
        return "Cliente"
    # Formato GDS: APELLIDO/NOMBRE o APELLIDO/NOMBRE MR / MRS / CHD
    if "/" in nombre_completo:
        parts = nombre_completo.split("/")
        if len(parts) > 1:
            nombre_words = parts[1].strip().split()
            titulos = {"MR", "MRS", "MS", "MISS", "MSTR", "DR", "PROF", "CHD", "INF", "SR", "SRA"}
            clean_words = [w for w in nombre_words if w.upper() not in titulos]
            if clean_words:
                return " ".join(clean_words).title()
            if nombre_words:
                return nombre_words[0].title()
    return nombre_completo.strip().split()[0].title()


class FastDeterministicParsers:
    """
    🛡️ EL ESCUDO DETERMINÍSTICO (Regex)
    Reglas de extracción rápidas y gratuitas para cuando la IA falla o para ahorrar costos.
    """

    @staticmethod
    def parse_general_regex(text: str) -> dict[str, Any]:
        """
        Intenta extraer lo básico (Nombre, PNR, Ticket, Itinerario) usando patrones comunes.
        """
        data = {"flights": []}
        text_upper = text.upper()

        # 0. Detectar aerolínea una sola vez; se usa para el prefijo del boleto
        #    y para el campo aerolinea_emisora.
        airline = _detect_airline(text_upper)

        # 1. Extraer PNR / Localizador (GDS)
        # Soporta acentos (Ó) y el símbolo +
        pnr_match = re.search(
            r"(?:RESERVACI[OÓ]N|RESERVA|CODE|PNR|LOCALIZADOR|RECORD|BOOKING REF)[:\s\n]+([A-Z0-9]{6,8})",
            text_upper,
        )
        if pnr_match:
            data["codigo_reserva"] = pnr_match.group(1).replace("+", "")

        # 1b. Extraer PNR de Aerolínea (Específico)
        # Buscamos patrones como "CÓDIGO DE RESERVACIÓN DE LA AEROLÍNEA" o "AIRLINE CONFIRMATION"
        # Usamos re.sub para normalizar espacios y saltos de línea antes de buscar.
        normalized_text = re.sub(r"\s+", " ", text_upper)
        air_pnr_patterns = [
            r"(?:C[OÓ]DIGO\s+DE\s+)?RESERVACI[OÓ]N\s+DE\s+LA\s+AEROL[IÍ]NEA[:\s]+([A-Z0-9]{6})",
            r"(?:C[OÓ]DIGO\s+DE\s+)?RESERVA\s+DE\s+LA\s+AEROL[IÍ]NEA[:\s]+([A-Z0-9]{6})",
            r"AIRLINE\s+RESERVATION\s+CODE[:\s]+([A-Z0-9]{6})",
            r"CONFIRMACI[OÓ]N\s+AEROL[IÍ]NEA[:\s]+([A-Z0-9]{6})",
            r"AIRLINE\s+CONFIRMATION[:\s]+([A-Z0-9]{6})",
        ]

        for pattern in air_pnr_patterns:
            air_match = re.search(pattern, normalized_text)
            if air_match:
                pnr_val = air_match.group(1).strip()
                data["pnr_aerolinea"] = pnr_val
                data["airline_pnr"] = pnr_val
                break

        # Reintento si falló (Búsqueda más agresiva)
        if "airline_pnr" not in data:
            # Patrón para: Código de reservación de la aerolínea ABCDEF
            aggressive_match = re.search(
                r"RESERVACI[OÓ]N\s+DE\s+LA\s+AEROL[IÍ]NEA\s+([A-Z0-9]{6})", normalized_text
            )
            if aggressive_match:
                data["airline_pnr"] = aggressive_match.group(1)

        # 2. Extraer Número de Boleto (13 dígitos)
        #    Acepta prefijo opcional de aerolínea (3 dígitos IATA). Si el boleto
        #    viene con 10 dígitos, se recompone con el prefijo de la aerolínea
        #    detectada (solo si es un código IATA conocido; nunca se inventa).
        tkt_match = re.search(
            r"(?:BOLETO|TICKET|ETKT|NUMERO|TKTN)[:\s]+(?:(\d{3})-?)?([0-9]{10,13})",
            text_upper,
        )
        if tkt_match:
            tkt = tkt_match.group(2)
            if len(tkt) == 10:
                iata_prefix = AIRLINE_IATA_CODES.get(airline) if airline else None
                if iata_prefix:
                    tkt = iata_prefix + tkt
            data["numero_boleto"] = tkt

        # 3. Extraer Nombre del Pasajero y Documento
        # Soporta: NOMBRE [DOCUMENTO] o NOMBRE FOID: XXX
        # Mejorado para evitar capturar FOID/RIF como parte del nombre
        name_match = re.search(
            r"(?:PREPARADO PARA|PASAJERO|PASSENGER|NAME|PAX)[:\s]+([^[\n\r<]{3,60})", text_upper
        )
        if name_match:
            raw_name = name_match.group(1).strip()
            # Limpiar ruidos comunes (FOID, RIF, etc.) y detenerse en el primer marcador de metadatos
            # Añadimos más marcadores para evitar que el nombre "se coma" otros campos
            clean_name = re.split(
                r"\s+(?:FOID|RIF|DNI|DOCUMENTO|DOC|TKTN|C\.I|V-|ADDRESS|TEL|PHONE|IATA|ISSUING|AGENTE|OFFICE)\b",
                raw_name,
                flags=re.IGNORECASE,
            )[0]
            data["nombre_pasajero"] = clean_name.strip()

            # Extraer ID (Buscamos dentro de corchetes o después de FOID:)
            # Usamos negative lookahead para ignorar IDs de sistema (imágenes, oficinas)
            id_match = re.search(
                r"\[(?!IMAGEN_|OFFICE|PA-|VE-|US-|PHOTO|PNG|JPG)([^\]]+)\]", text_upper
            )
            if not id_match:
                id_match = re.search(
                    r"(?:FOID|RIF|DNI|DOCUMENTO|DOC|C\.I|V-)[:\s]+(?!PA-|VE-|US-|OFFICE)([A-Z0-9-]{6,20})",
                    text_upper,
                )

            if id_match:
                pax_id = id_match.group(1).strip()
                # Doble filtro de seguridad para IDs de ruido
                if not any(
                    noise in pax_id
                    for noise in ["IMAGEN_", "PA-", "VE-", "US-", "OFFICE", "PHOTO", "PNG", "JPG"]
                ):
                    data["foid"] = pax_id
                    data["passenger_id"] = pax_id

        # 4. Extraer Aerolínea (usando la detección centralizada del paso 0)
        if airline:
            data["aerolinea_emisora"] = airline

        # 5. Extraer Fecha de Emisión
        date_match = re.search(
            r"(?:EMISION|ISSUED|DATE|FECHA)[:\s]+(\d{1,2}\s+[A-Z]{3}\s+\d{2,4})", text_upper
        )
        if date_match:
            data["fecha_emision"] = date_match.group(1)
        else:
            # Reintento para formato abreviado (29 ABR 26). Se acota a la cabecera
            # del boleto (antes del primer segmento de vuelo, incl. bloque multi-línea
            # de Turkish) para no confundir la fecha de emisión con la fecha de un
            # vuelo del itinerario (P2-29).
            first_seg = re.search(
                r"(?:\d+\s+)?(?:[A-Z0-9]{2}\s*\d{1,4}\s*[A-Z]?\s*\d{2}[A-Z]{3}\s+"
                r"|\d{1,2}\s+[A-Z]{3}\s+\d{2,4}\s+TURKISH AIRLINES)",
                text_upper,
            )
            header_region = text_upper[: first_seg.start()] if first_seg else text_upper
            date_match = re.search(r"(\d{1,2}\s+[A-Z]{3}\s+\d{2})", header_region)
            if date_match:
                data["fecha_emision"] = date_match.group(1)

        # 6. Extraer Itinerario (Vuelos) - Motor de Segmentos GDS Pro (Audit Point 2)
        # Pre-limpieza de texto para eliminar bloques de ruido conocidos en Sabre
        lines = text_upper.splitlines()
        clean_lines = []
        for line in lines:
            ls = line.strip()
            # Ignorar líneas que suelen ser ruido entre vuelos
            if any(
                x in ls
                for x in [
                    "VIEWTRIP",
                    "CHECK-IN",
                    "BAGGAGE",
                    "EQUIPAJE",
                    "URL",
                    "HTTPS",
                    "CO2",
                    "EMISSION",
                    "OPERATED BY",
                ]
            ):
                continue
            clean_lines.append(ls)
        text_for_flights = "\n".join(clean_lines)

        # Patrón ultra-robusto para Sabre/Amadeus:
        # Soporta: 1 AV 46 C 22MAY BOGMAD HK1 0700 2330
        # Soporta: AV46C 22MAY BOGMAD HK1 0700A 2330P
        flight_pattern = re.compile(
            r"(?:\d+\s+)?"  # Index opcional (1 )
            r"([A-Z0-9]{2})\s*"  # Aerolinea (AV)
            r"(\d{1,4})\s*"  # Numero de vuelo (46)
            r"([A-Z])?\s*"  # Clase (C) opcional
            r"(\d{2}[A-Z]{3})\s+"  # Fecha (22MAY)
            r"(?:\d\s+)?"  # Día de semana opcional (4 )
            r"([A-Z]{3})\s*([A-Z]{3})\s+"  # Origen y Destino (BOGMAD o BOG MAD)
            r"([A-Z0-9]{2,3})\s+"  # Status (HK1)
            r"(\d{4}[A-Z]?)\s+"  # Salida (0700A)
            r"(\d{4}[A-Z]?)"  # Llegada (2330P)
        )

        matches = flight_pattern.findall(text_for_flights)

        for m in matches:
            # Normalizar horas (0700A -> 07:00, 2330 -> 23:30)
            def norm_h(h):
                """norm_h."""
                h = re.sub(r"[A-Z]", "", h)  # Quitar A/P
                if len(h) == 4:
                    return f"{h[:2]}:{h[2:]}"
                return h

            dep_time = norm_h(m[7])
            arr_time = norm_h(m[8])

            flight = {
                "airline": m[0],
                "flightNumber": f"{m[0]} {m[1]}",
                "date": m[3],
                "departure": {"location": m[4], "time": dep_time},
                "arrival": {"location": m[5], "time": arr_time},
                "status": m[6] or "CONFIRMADO",
                # Compatibilidad
                "origen": m[4],
                "destino": m[5],
                "vuelo": f"{m[0]} {m[1]}",
                "fecha_salida": m[3],
                "hora_salida": dep_time,
                "hora_llegada": arr_time,
            }
            data["flights"].append(flight)

        # 7. Reintento específico para Turkish Airlines (Formato multi-línea)
        if not data["flights"]:
            # Buscamos bloques que empiecen con fecha y aerolínea
            # Ejemplo: 12 may 26 TURKISH AIRLINES SHANGHAI PUDONG, ISTANBUL AIRPORT ... TK 281
            tk_blocks = re.split(r"(\d{1,2}\s+[A-Z]{3}\s+\d{2,4}\s+TURKISH AIRLINES)", text_upper)
            if len(tk_blocks) > 1:
                for i in range(1, len(tk_blocks), 2):
                    header = tk_blocks[i]
                    content = tk_blocks[i + 1] if i + 1 < len(tk_blocks) else ""

                    date_match = re.search(r"(\d{1,2}\s+[A-Z]{3}\s+\d{2,4})", header)
                    loc_match = re.search(
                        r"TURKISH AIRLINES\s+([^,]+),\s+([^\n,]+)", header + content
                    )
                    fn_match = re.search(r"TK\s*(\d{1,4})", content)

                    # Localizador de aerolínea (UQZIPR) - Soporta multi-línea
                    # Patrones específicos para Sabre: "CÓDIGO DE RESERVACIÓN DE LA AEROLÍNEA" o similares
                    air_pnr_match = re.search(
                        r"(?:RESERVACI[OÓ]N\s+DE\s+LA\s+AEROL[IÍ]NEA|AIRLINE\s+CONFIRMATION|C[OÓ]DIGO\s+DE\s+RESERVACI[OÓ]N\s+DE\s+LA\s+AEROL[IÍ]NEA)[:\s\n]+([A-Z0-9]{6})",
                        content.replace("\n", " "),
                    )
                    if not air_pnr_match:
                        # Intento con el texto largo "reservación de la aerolínea"
                        air_pnr_match = re.search(
                            r"RESERVACI[OÓ]N\s+DE\s+LA\s+AEROL[IÍ]NEA\s+([A-Z0-9]{6})",
                            content.replace("\n", " "),
                        )
                    if not air_pnr_match:
                        # Intento genérico para AIRLINE PNR
                        air_pnr_match = re.search(
                            r"(?:AEROL[IÍ]NEA|AIRLINE)[:\s\n]+([A-Z0-9]{6})", content
                        )

                    # Horas (07:55 14:50)
                    times_match = re.search(r"(\d{2}:\d{2})\s+(\d{2}:\d{2})", content)

                    if date_match and loc_match and fn_match:
                        data["flights"].append(
                            {
                                "airline": "TURKISH AIRLINES",
                                "flightNumber": f"TK {fn_match.group(1)}",
                                "date": date_match.group(1),
                                "origen": loc_match.group(1).strip(),
                                "destino": loc_match.group(2).strip(),
                                "departure": {
                                    "location": loc_match.group(1).strip(),
                                    "time": times_match.group(1) if times_match else "--",
                                },
                                "arrival": {
                                    "location": loc_match.group(2).strip(),
                                    "time": times_match.group(2) if times_match else "--",
                                },
                                "airline_pnr": air_pnr_match.group(1) if air_pnr_match else "",
                                "status": "CONFIRMADO",
                            }
                        )

        return data


@track_parser_execution("regex", "ticket_parsing")
def extract_data_from_text(
    plain_text: str, html_text: str = "", pdf_path: str | None = None, bypass_cache: bool = False
) -> dict[str, Any]:
    """
    ⚡ MOTOR DETERMINÍSTICO (Fallback Regex)
    Utiliza patrones fijos para extraer datos cuando la IA no está disponible o falla.
    Este es el motor de Tier 1 (Gratis).
    """
    if not plain_text:
        return {"error": "Texto vacío"}

    # 1. 🧱 CACHÉ (Evita procesar dos veces lo mismo)
    fingerprint = hashlib.sha256(plain_text.encode("utf-8", errors="ignore")).hexdigest()
    cache_key = f"parser:regex:{fingerprint}"

    if not bypass_cache:
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

    # 2. ⚡ PARSERS DETECTADOS (Sabre, Amadeus, KIU, etc.)
    # Primero intentamos usar los parsers robustos específicos de GDS
    try:
        from apps.automation.parsers.adapter import parse_ticket_with_new_parsers

        logger.info("Tentando extraer usando parsers robustos estructurados...")
        res_gds = parse_ticket_with_new_parsers(plain_text, html_text)
        if res_gds and not res_gds.get("error"):
            logger.info(" Extracción exitosa con parser específico de GDS.")
            # Normalizar claves legacy esperadas por ticket_parser_service
            if "codigo_reserva" not in res_gds and "pnr" in res_gds:
                res_gds["codigo_reserva"] = res_gds["pnr"]
            if "nombre_pasajero" not in res_gds and "passenger_name" in res_gds:
                res_gds["nombre_pasajero"] = res_gds["passenger_name"]

            # Guardar en caché
            cache.set(cache_key, res_gds, timeout=86400)
            return res_gds
        else:
            logger.warning(
                f"No se detectó parser específico compatible o devolvió error: {res_gds.get('error') if res_gds else 'None'}"
            )
    except Exception as e:
        logger.error(f"Error intentando usar parsers específicos: {e}", exc_info=True)

    # 3. ⚡ PATRONES DETERMINÍSTICOS GENÉRICOS (Gratis y Rápidos)
    logger.info("Usando parser regex genérico como último recurso (FastDeterministicParsers)...")
    res_final = FastDeterministicParsers.parse_general_regex(plain_text)

    # Normalizar claves para res_final
    if res_final:
        if "codigo_reserva" not in res_final and "pnr" in res_final:
            res_final["codigo_reserva"] = res_final["pnr"]
        if "nombre_pasajero" not in res_final and "passenger_name" in res_final:
            res_final["nombre_pasajero"] = res_final["passenger_name"]

        # Detección de GDS para compatibilidad
        purified = plain_text.upper()
        if "SABRE" in purified or "RECIBO DE PASAJE" in purified:
            res_final["gds"] = "sabre"
        elif "KIUSYS" in purified or "KIU" in purified:
            res_final["gds"] = "kiu"
        else:
            res_final["gds"] = "unknown"

    # 4. 💾 GUARDAR EN CACHÉ
    if res_final and (res_final.get("codigo_reserva") or res_final.get("nombre_pasajero")):
        cache.set(cache_key, res_final, timeout=86400)

    return res_final


def is_brand_color_dark(hex_color: str) -> bool:
    """is_brand_color_dark."""
    if not hex_color or not isinstance(hex_color, str):
        return True
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return True
    try:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        luma = 0.299 * r + 0.587 * g + 0.114 * b
        return luma < 128
    except (ValueError, IndexError):
        return True


def _parse_date_robust(date_str):
    """
    Intenta parsear fechas en formatos comunes de GDS (25APR, 25 APR 2024, etc)
    """
    if not date_str or str(date_str).strip() == "":
        return None

    date_str = str(date_str).upper().strip()
    # Limpieza de ruidos comunes
    date_str = re.sub(r"^(?:EMISION|ISSUED|DATE|FECHA)[:\s]+", "", date_str)

    from core.models.ai_schemas import MESES_ES_TO_EN

    for es, en in MESES_ES_TO_EN.items():
        if es in date_str:
            date_str = date_str.replace(es, en)

    from datetime import datetime

    formatos = ["%d%b", "%d %b", "%d %b %Y", "%d%b%y", "%d%b%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]

    # Intentar con meses en inglés (estándar GDS)
    for fmt in formatos:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Si no tiene año, asumimos el actual o el próximo según el mes
            if dt.year == 1900:
                now = datetime.now()
                dt = dt.replace(year=now.year)
                # Si el mes ya pasó hace mucho (ej: estamos en Dic y la fecha es Ene),
                # podría ser del año que viene, pero para emisión solemos usar el actual.
            return dt.date()
        except Exception as e:
            logger.debug("Ignored exception parsing date: %s", e)
            continue

    return None


def generate_ticket(data: dict[str, Any], agencia_obj=None, boleto_obj=None):
    """generate_ticket."""
    from apps.automation.parsers.pdf_generation import PdfGenerationService

    # Siempre pasamos el objeto de boleto si viene en la data para asegurar persistencia
    return PdfGenerationService.generate_ticket(
        data, agencia_obj, boleto_obj=boleto_obj or data.get("_boleto_instance")
    )

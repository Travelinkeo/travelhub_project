import logging
import quopri
import re
from decimal import Decimal
from typing import Any

from bs4 import BeautifulSoup

from apps.automation.parsers.base_parser import BaseTicketParser, ParsedTicketData

logger = logging.getLogger(__name__)


class CopaParser(BaseTicketParser):
    """Parser para boletos de Copa Airlines (sistema SPRK) - Extracción completa desde HTML"""

    def can_parse(self, text: str) -> bool:
        purified = self.purify_text_for_detection(text)
        has_copa = "COPA AIRLINES" in purified or "COPA" in purified
        has_locator = (
            "RECORD LOCATOR" in purified
            or "LOCALIZADOR" in purified
            or "CODIGO DE RESERVACION" in purified
        )
        has_itinerary = "ITINERARY" in purified or "ITINERARIO" in purified
        is_sabre = "RECIBO DE PASAJE" in purified or "ETICKET RECEIPT" in purified
        return bool((has_copa and (has_locator or has_itinerary)) and not is_sabre)

    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        # Decodificar quoted-printable si es necesario
        decoded_text = self._decode_quoted_printable(text)

        # Extracción de campos principales
        pnr = self._extract_pnr(decoded_text)
        airline_pnr = self._extract_airline_pnr(decoded_text)
        ticket_number = self._extract_ticket_number(decoded_text)
        issue_date = self._extract_issue_date(decoded_text)
        passenger_data = self._extract_passenger(decoded_text)
        agency_data = self._extract_agency(decoded_text)
        flights = self._extract_flights(decoded_text)
        fares = self._extract_amounts(decoded_text)

        return ParsedTicketData(
            source_system="COPA_SPRK",
            pnr=pnr,
            ticket_number=ticket_number,
            passenger_name=passenger_data.get("nombre_completo", "No encontrado"),
            issue_date=issue_date,
            flights=flights,
            fares=fares,
            agency=agency_data,
            raw_data={
                "pasajero": passenger_data,
                "vuelos": flights,
                "fecha_creacion": issue_date,
                "agencia": agency_data,
                "agencia_iata": agency_data.get("iata", "N/A"),
                "localizador_aerolinea": airline_pnr,
            },
        )

    def _decode_quoted_printable(self, text: str) -> str:
        """Decodifica texto quoted-printable y limpia entidades HTML comunes"""
        try:
            decoded = quopri.decodestring(text.encode()).decode("utf-8", errors="ignore")
            decoded = decoded.replace("\u0026nbsp;", " ")
            decoded = decoded.replace("\u0026amp;", "&")
            return decoded
        except Exception as e:
            logger.warning(f"⚠️ Error decodificando quoted-printable: {e}")
            return text

    def _get_html_soup(self, text: str) -> BeautifulSoup:
        """Extrae la parte HTML del email y la convierte en BeautifulSoup"""
        # Busca la sección HTML entre los encabezados y la siguiente frontera
        html_match = re.search(
            r"Content-Type:\s*text/html;.*?\r\n\r\n(.*?)(?:\r\n--|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if not html_match:
            return None
        html_content = html_match.group(1)
        # Algunas partes pueden estar codificadas en base64; intenta decodificar
        try:
            decoded_html = quopri.decodestring(html_content.encode()).decode(
                "utf-8", errors="ignore"
            )
        except Exception:
            decoded_html = html_content
        return BeautifulSoup(decoded_html, "html.parser")

    def _extract_pnr(self, text: str) -> str:
        """Extrae el PNR/Record Locator del sistema SPRK"""
        patterns = [
            r"Itinerary for Record Locator\s+<b>([A-Z0-9]{6})</b>",
            r"Itinerary for Record Locator\s+([A-Z0-9]{6})",
            r"Itinerario para localizador de reserva\s+<b>([A-Z0-9]{6})</b>",
            r"Itinerario para localizador de reserva\s+([A-Z0-9]{6})",
            r"Record Locator\s*[:\.]?\s*([A-Z0-9]{6})",
            r"Localizador de reserva\s*[:\.]?\s*([A-Z0-9]{6})",
        ]
        return self.extract_field(text, patterns)

    def _extract_airline_pnr(self, text: str) -> str:
        """Extrae el Record Locator de la aerolínea (Copa Airlines Record Locator)"""
        patterns = [
            r"Copa Airlines Record Locator\s+([A-Z0-9]{6})",
            r"Localizador de reserva de Copa Airlines\s+([A-Z0-9]{6})",
            r"Copa Airlines Localizador de reserva\s*\n*\s*([A-Z0-9]{6})",
            r"Copa Loc:\s*([A-Z0-9]{6})",
        ]
        return self.extract_field(text, patterns, default="N/A")

    def _extract_ticket_number(self, text: str) -> str:
        """Extrae el número de boleto electrónico (Document Number)"""
        patterns = [
            r"Electronic Ticket\s+(\d{13})",
            r"Ticket Number\s*[:\s]?\s*(\d{6,})",
            r"Document Number\s*[:\s]?\s*(\d{6,})",
        ]
        return self.extract_field(text, patterns, default="No encontrado")

    def _extract_issue_date(self, text: str) -> str:
        """Extrae la fecha de emisión del boleto, preferentemente desde la sección HTML."""
        soup = self._get_html_soup(text)
        if soup:
            # Busca etiquetas que contengan alguna de las expresiones clave
            label_text = soup.find_all(
                text=re.compile(r"Issue Date|Fecha de Emisión|Date of Issue", re.IGNORECASE)
            )
            for label in label_text:
                match = re.search(
                    r"(?:Issue Date|Fecha de Emisión|Date of Issue)[:\s]*([A-Za-z0-9 ,]+)",
                    label,
                    re.IGNORECASE,
                )
                if match:
                    return match.group(1).strip()
        # Fallback to plain-text regex extraction
        patterns = [
            r"Issue Date\s*[:\s]?\s*([A-Za-z0-9 ,]+)",
            r"Fecha de Emisión\s*[:\s]?\s*([A-Za-z0-9 ,]+)",
            r"Date of Issue\s*[:\s]?\s*([A-Za-z0-9 ,]+)",
        ]
        return self.extract_field(text, patterns, default="No encontrado")

    def _clean_passenger_name(self, name: str) -> str:
        """Normaliza el nombre del pasajero eliminando títulos y caracteres extra."""
        if not name:
            return ""
        # Elimina prefijos como "PM", "E Y S", etc.
        name = re.sub(r"^(PM|E\s*Y\s*S)\s*", "", name, flags=re.IGNORECASE)
        # Elimina caracteres no alfabéticos al final
        name = re.sub(r"[\[\]\-_/]+$", "", name)
        return name.strip()

    def _extract_passenger(self, text: str) -> dict[str, str]:
        """Extrae datos del pasajero (nombre completo) usando HTML cuando sea posible."""
        # Intentar obtener el nombre desde el HTML
        soup = self._get_html_soup(text)
        if soup:
            # Busca etiquetas que contengan 'Prepared For' o su versión en español
            possible_labels = soup.find_all(
                text=re.compile(r"Prepared For|Preparado para", re.IGNORECASE)
            )
            for label in possible_labels:
                # El nombre suele estar en el mismo elemento o en el siguiente sibling
                parent = label.parent
                # Si el texto del label ya contiene el nombre después de los dos puntos
                match = re.search(
                    r"(?:Prepared For|Preparado para)[:\s]*([A-ZÁÉÍÓÚ0-9\-\[\]\s,\.]+)",
                    label,
                    re.IGNORECASE,
                )
                if match:
                    raw_name = match.group(1)
                    clean_name = self._clean_passenger_name(raw_name)
                    if clean_name:
                        return {"nombre_completo": clean_name}
                # Caso en que el nombre está en el siguiente sibling text
                next_text = parent.find_next_sibling(text=True)
                if next_text:
                    raw_name = next_text.strip()
                    clean_name = self._clean_passenger_name(raw_name)
                    if clean_name:
                        return {"nombre_completo": clean_name}
        # Fallback to plain-text regex extraction
        patterns = [
            r"(?:Prepared For|Preparado para)\s*[:\n\r]*\s*([A-ZÁÉÍÓÚ0-9\-\[\]\s,\.]+?)(?:\s*\[|\n|$)",
            r"Passenger\s*[:\n\r]*\s*([A-ZÁÉÍÓÚ0-9\-\[\]\s,\.]+?)(?:\s*\[|\n|$)",
        ]
        raw_name = self.extract_field(text, patterns, default="No encontrado")
        clean_name = self._clean_passenger_name(raw_name)
        return {"nombre_completo": clean_name if clean_name else "No encontrado"}

    def _clean_location(self, location: str) -> str:
        """Limpia texto de ubicación para quedarse solo con la ciudad."""
        if not location:
            return ""
        loc = re.sub(r"\(.*?\)", "", location)
        loc = re.sub(
            r"\b(airport|terminal|terminal\s*\d+|satellite)\b", "", loc, flags=re.IGNORECASE
        )
        return loc.strip()

    def _extract_agency(self, text: str) -> dict[str, str]:
        """Extrae información de la agencia emisora (nombre y código IATA)."""
        name_patterns = [
            r"(?:Issuing Agent|AGENTE EMISOR|Agente Emisor)\s*[:\n\r]*\s*([^\n]+)",
        ]
        iata_patterns = [
            r"(?:IATA Number|IATA|N[úU]mero IATA|NÚMERO IATA|NMERO IATA)\s*[:\n\r]*\s*([0-9]+)",
        ]
        agency_name = self.extract_field(text, name_patterns, default="No encontrado")
        iata = self.extract_field(text, iata_patterns, default="N/A")
        return {"nombre": agency_name, "iata": iata}

    def _extract_flights(self, text: str) -> list[dict[str, Any]]:
        """Extrae la lista de vuelos contenidos en el itinerario, soportando HTML.
        Primero intenta parsear una tabla HTML con encabezados típicos; si no se encuentra,
        se recurre al patrón de texto plano anterior.
        """
        flights: list[dict[str, Any]] = []
        soup = self._get_html_soup(text)
        if soup:
            # Buscar tabla que contenga cabezales de vuelo
            tables = soup.find_all("table")
            for tbl in tables:
                headers = [th.get_text(strip=True).lower() for th in tbl.find_all("th")]
                if any("flight" in h for h in headers) and any("date" in h for h in headers):
                    for row in tbl.find_all("tr")[1:]:  # saltar encabezado
                        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                        if len(cells) < 6:
                            continue
                        # Asumir posición basada en encabezados comunes
                        # Intentar mapear: Flight Number, Date, Origin, Dep Time, Destination, Arr Time
                        f_num = cells[0]
                        f_date = cells[1]
                        origin_raw = cells[2]
                        dep_time = cells[3]
                        dest_raw = cells[4]
                        arr_time = cells[5]
                        origin = self._clean_location(origin_raw)
                        destination = self._clean_location(dest_raw)
                        flights.append(
                            {
                                "aerolinea": "Copa Airlines",
                                "numero_vuelo": f_num.strip(),
                                "origen": origin,
                                "fecha_salida": f_date.upper(),
                                "hora_salida": dep_time.strip(),
                                "destino": destination,
                                "hora_llegada": arr_time.strip(),
                                "cabina": "Económica",
                                "clase": "L",
                            }
                        )
                    if flights:
                        return flights  # Si se encontraron vuelos en HTML, finalizar
        # Fallback al patrón de texto plano (mantener el original)
        flight_pattern = re.compile(
            r"Flight\s*Number\s*[:\s]?\s*([A-Z0-9]+).*?"  # número de vuelo
            r"Date\s*[:\s]?\s*(\d{1,2}[A-Z]{3})"  # fecha (ej 15JAN)
            r".*?Origin\s*[:\s]?\s*([^\n]+?)\s+([0-9]{2}:[0-9]{2}\s*[AP]M)"  # origen y hora salida
            r".*?Destination\s*[:\s]?\s*([^\n]+?)\s+([0-9]{2}:[0-9]{2}\s*[AP]M)",  # destino y hora llegada
            re.DOTALL | re.IGNORECASE,
        )
        for match in flight_pattern.finditer(text):
            f_num, f_date, origin_raw, dep_time, dest_raw, arr_time = match.groups()
            origin = self._clean_location(origin_raw)
            destination = self._clean_location(dest_raw)
            flights.append(
                {
                    "aerolinea": "Copa Airlines",
                    "numero_vuelo": f_num.strip(),
                    "origen": origin,
                    "fecha_salida": f_date.upper(),
                    "hora_salida": dep_time.strip(),
                    "destino": destination,
                    "hora_llegada": arr_time.strip(),
                    "cabina": "Económica",
                    "clase": "L",
                }
            )
        return flights

    def _extract_amounts(self, text: str) -> list[dict[str, Any]]:
        """Extrae los importes (fare) encontrados en el texto.
        Busca la sección de totales y devuelve una lista de dicts con label y amount.
        """
        amounts: list[dict[str, Any]] = []
        soup = self._get_html_soup(text)
        if soup:
            # Intentar localizar la tabla o sección que contiene la palabra 'Fare' o 'Total'
            fare_text = soup.get_text(separator="\n")
            lines = fare_text.split("\n")
            for line in lines:
                if re.search(r"fare|total", line, re.IGNORECASE):
                    match = re.search(
                        r"([A-Za-z ]+?)\s*[:\s]?\s*\$?([\d,]+\.\d{2})", line, re.IGNORECASE
                    )
                    if match:
                        label, value = match.groups()
                        try:
                            amount = Decimal(value.replace(",", ""))
                            amounts.append({"label": label.strip(), "amount": amount})
                        except Exception:
                            continue
        # Fallback al regex genérico sobre el texto plano
        amount_pattern = re.compile(r"([A-Za-z ]+?)\s*[:\s]?\s*\$?([\d,]+\.\d{2})")
        for label, value in amount_pattern.findall(text):
            try:
                amount = Decimal(value.replace(",", ""))
            except Exception:
                continue
            amounts.append({"label": label.strip(), "amount": amount})
        return amounts

    # Métodos auxiliares heredados de BaseTicketParser pueden ser usados directamente

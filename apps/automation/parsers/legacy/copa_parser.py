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
        """can_parse."""
        text_upper = text.upper()
        return (
            "COPA AIRLINES" in text_upper
            and ("COPAAIRLINES.COM" in text_upper or "RESERVA" in text_upper)
            and (
                "COMPROBANTE DE PAGO" in text_upper
                or "RECEIPT" in text_upper
                or "ITINERARIO" in text_upper
            )
        )

    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        """parse."""
        # Decodificar quoted-printable si es necesario
        decoded_text = self._decode_quoted_printable(text)
        decoded_html = self._decode_quoted_printable(html_text) if html_text else ""

        # Extracción de campos principales
        pnr = self._extract_pnr(decoded_text)
        airline_pnr = self._extract_airline_pnr(decoded_html if decoded_html else decoded_text)
        ticket_number = self._extract_ticket_number(decoded_html if decoded_html else decoded_text)
        issue_date = self._extract_issue_date(decoded_text, html_text=decoded_html)
        passenger_data = self._extract_passenger(decoded_text, html_text=decoded_html)
        agency_data = self._extract_agency(decoded_text)
        flights = self._extract_flights(decoded_text, html_text=decoded_html)
        fares = self._extract_amounts(decoded_text, html_text=decoded_html)

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
            logger.warning(f" Error decodificando quoted-printable: {e}")
            return text

    def _get_html_soup(self, text: str, html_text: str = "") -> BeautifulSoup:
        """Extrae la parte HTML y la convierte en BeautifulSoup"""
        if html_text:
            return BeautifulSoup(html_text, "html.parser")

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
            r"Copa(?:\s+Airlines)?(?:\s+Indirect)?\s+Localizador de reserva\s+([A-Z0-9]{6})",
            r"Copa Indirect Localizador de reserva\s+([A-Z0-9]{6})",
            r"Copa Airlines Record Locator\s+([A-Z0-9]{6})",
            r"Localizador de reserva de Copa Airlines\s+([A-Z0-9]{6})",
            r"Copa Loc:\s*([A-Z0-9]{6})",
        ]
        return self.extract_field(text, patterns, default="N/A")

    def _extract_ticket_number(self, text: str) -> str:
        """Extrae el número de boleto electrónico (Document Number)

        Copa Airlines: ExtractionService._clean_html() concatenates table cells WITHOUT
        separators, producing lines like: 'Billete electrónico230752374111614JUL.26'
        The 13-digit ticket number is embedded directly after 'electrónico'.
        """
        # Strategy 1: Line-by-line scan for concatenated format
        # 'Billete electrónico<13-digit-number><date>'
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        for line in lines:
            if re.search(r"Billete\s+electr", line, re.IGNORECASE):
                # Extract the 10-13 digit number embedded in the line
                m = re.search(r"electr\S*nico\s*(\d{10,13})", line, re.IGNORECASE)
                if m:
                    return m.group(1)
                # Also try finding any 13-digit sequence on the line
                m2 = re.search(r"(\d{13})", line)
                if m2:
                    return m2.group(1)
                # Try 10+ digit sequence
                m3 = re.search(r"(\d{10,})", line)
                if m3:
                    return m3.group(1)
                # Number may be on the NEXT line (when HTML is better formatted)
                idx = lines.index(line) if line in lines else -1
                if idx >= 0:
                    for j in range(idx + 1, min(idx + 4, len(lines))):
                        if re.match(r"^\d{10,}$", lines[j].strip()):
                            return lines[j].strip()

        # Strategy 2: Regex patterns across full text
        patterns = [
            r"Billete electr.nico\s*(\d{10,13})",
            r"Electronic Ticket[\s\n\r]+(\d{10,})",
            r"Ticket Number\s*[:\s]?\s*(\d{6,})",
            r"Document Number\s*[:\s]?\s*(\d{6,})",
        ]
        return self.extract_field(text, patterns, default="No encontrado")

    def _extract_issue_date(self, text: str, html_text: str = "") -> str:
        """Extrae la fecha de emisión del boleto, preferentemente desde la sección HTML."""
        # Copa HTML text has structure:
        # 'Número de documento'\n'Fecha de emisión'\n'Billete electrónico'\n'2307523741116'\n'14JUL.26'
        # so date comes 2 lines after 'Fecha de emisión'
        search_text = html_text if html_text else text
        lines = [ln.strip() for ln in search_text.split("\n") if ln.strip()]
        for i, line in enumerate(lines):
            if re.search(r"fecha\s+de\s+emisi", line, re.IGNORECASE):
                # The date is typically 2 lines after (after 'Billete electrónico' and ticket number)
                # But scan ahead up to 5 lines for a date pattern
                for j in range(i + 1, min(i + 6, len(lines))):
                    date_match = re.match(r"^(\d{1,2}[A-Z]{3}\.?\d{0,4})$", lines[j].strip())
                    if date_match:
                        return date_match.group(1)
                    # Also match patterns like '14JUL.26' or '14 JUL 2026'
                    date_match2 = re.search(r"(\d{1,2}\s*[A-Za-z]{3}[.\.\s]*\d{2,4})", lines[j])
                    if date_match2:
                        return date_match2.group(1)
        # Fallback regex
        patterns = [
            r"Fecha\s+de\s+emisi[oó]n[\s\n\r]+(?:Billete[^\n]*\n)?([\d]{10,}[\n\r]+)?(\d{1,2}[A-Z]{3}\.?\d{0,4})",
            r"Issue Date\s*[:\s]?\s*([A-Za-z0-9 ,]+)",
            r"Date of Issue\s*[:\s]?\s*([A-Za-z0-9 ,]+)",
        ]
        for p in patterns:
            m = re.search(p, search_text, re.IGNORECASE | re.MULTILINE)
            if m:
                return m.group(m.lastindex).strip()
        return "No encontrado"

    def _clean_passenger_name(self, name: str) -> str:
        """Normaliza el nombre del pasajero eliminando títulos y caracteres extra."""
        if not name:
            return ""
        # Elimina prefijos como "PM", "E Y S", etc.
        name = re.sub(r"^(PM|E\s*Y\s*S)\s*", "", name, flags=re.IGNORECASE)
        # Elimina caracteres no alfabéticos al final
        name = re.sub(r"[\[\]\-_/]+$", "", name)
        return name.strip()

    def _extract_passenger(self, text: str, html_text: str = "") -> dict[str, str]:
        """Extrae datos del pasajero (nombre completo) usando HTML cuando sea posible.

        Copa Airlines EML format: passenger name appears as 'NOMBRE APELLIDO (ADT)'
        after each flight row and also in the 'Información de la factura' section.
        """
        search_text = html_text if html_text else text

        # Strategy 1: Find 'NOMBRE (ADT/CHD/INF)' pattern - very common in Copa HTML text
        adt_pattern = re.compile(
            r"^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{5,})\s+\((?:ADT|CHD|INF)\)", re.MULTILINE
        )
        for line in search_text.split("\n"):
            m = adt_pattern.match(line.strip())
            if m:
                raw_name = m.group(1).strip()
                clean_name = self._clean_passenger_name(raw_name)
                if clean_name and len(clean_name) > 5:
                    return {"nombre_completo": clean_name}

        # Strategy 2: Search in HTML soup
        soup = self._get_html_soup(text, html_text)
        if soup:
            # Copa puts passenger name in table cells like 'LUISANA MARTINEZ ARTEAGA (ADT)'
            for td in soup.find_all(["td", "span", "p"]):
                td_text = td.get_text(strip=True)
                m = re.match(r"^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{5,})\s+\((?:ADT|CHD|INF)\)", td_text)
                if m:
                    raw_name = m.group(1).strip()
                    clean_name = self._clean_passenger_name(raw_name)
                    if clean_name:
                        return {"nombre_completo": clean_name}

            # Strategy 3: 'Prepared For' label
            possible_labels = soup.find_all(
                text=re.compile(r"Prepared For|Preparado para", re.IGNORECASE)
            )
            for label in possible_labels:
                match = re.search(
                    r"(?:Prepared For|Preparado para)[:\s]*([A-ZÁÉÍÓÚ0-9\-\[\]\s,\.]+)",
                    str(label),
                    re.IGNORECASE,
                )
                if match:
                    raw_name = match.group(1)
                    clean_name = self._clean_passenger_name(raw_name)
                    if clean_name:
                        return {"nombre_completo": clean_name}

        # Fallback regex on combined text
        patterns = [
            r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{5,})\s+\((?:ADT|CHD|INF)\)",
            r"(?:Prepared For|Preparado para)\s*[:\n\r]*\s*([A-ZÁÉÍÓÚ0-9\-\[\]\s,\.]+?)(?:\s*\[|\n|$)",
        ]
        for p in patterns:
            m = re.search(p, search_text, re.IGNORECASE | re.MULTILINE)
            if m:
                raw_name = m.group(1).strip()
                clean_name = self._clean_passenger_name(raw_name)
                if clean_name and len(clean_name) > 5:
                    return {"nombre_completo": clean_name}

        return {"nombre_completo": "No encontrado"}

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
            r"([^\n]+?)\s*(?:No\.\s*IATA|IATA Number)",
        ]
        iata_patterns = [
            r"(?:IATA Number|IATA|N[úU]mero IATA|NÚMERO IATA|NMERO IATA)\s*[:\n\r]*\s*([0-9]+)",
        ]
        agency_name = self.extract_field(text, name_patterns, default="No encontrado")
        iata = self.extract_field(text, iata_patterns, default="N/A")
        return {"nombre": agency_name, "iata": iata}

    def _extract_flights(self, text: str, html_text: str = "") -> list[dict[str, Any]]:
        """Extrae la lista de vuelos contenidos en el itinerario, soportando HTML.
        Primero intenta parsear una tabla HTML con encabezados típicos; si no se encuentra,
        se recurre al patrón de texto plano anterior.
        """
        flights: list[dict[str, Any]] = []
        soup = self._get_html_soup(text, html_text)
        if soup:
            # Buscar tabla que contenga cabezales de vuelo
            tables = soup.find_all("table")
            for tbl in tables:
                headers = [th.get_text(strip=True).lower() for th in tbl.find_all("th")]
                if any("flight" in h or "vuelo" in h for h in headers):
                    for row in tbl.find_all("tr")[1:]:  # saltar encabezado
                        cells = [
                            c.get_text(separator=" ", strip=True)
                            for c in row.find_all(["td", "th"])
                        ]
                        if len(cells) < 6:
                            continue
                        # Asumir posición basada en encabezados comunes
                        # Puede variar dependiendo del idioma (español o inglés)
                        try:
                            # Caso EML Copa en español (0:Aerolínea, 1:Vuelo, 2:Origen, 3:Salida_Hora, 4:Destino, 5:Llegada_Hora, 6:Clase, 7:Cabina)
                            if "llegada" in str(headers) or "vuelo" in str(headers):
                                f_num = cells[1]
                                origin_raw = cells[2]
                                f_date_salida = cells[3]
                                dest_raw = cells[4]
                                f_date_llegada = cells[5]

                                # Extraer fecha y hora de f_date_salida ("LU. 20JUL. 01:38 PM")
                                s_match = re.search(
                                    r"([A-Z]{2}\.\s*\d{1,2}[A-Z]{3}\.)?\s*(\d{1,2}:\d{2}\s*[AP]M)",
                                    f_date_salida,
                                )
                                ll_match = re.search(
                                    r"([A-Z]{2}\.\s*\d{1,2}[A-Z]{3}\.)?\s*(\d{1,2}:\d{2}\s*[AP]M)",
                                    f_date_llegada,
                                )

                                if s_match and ll_match:
                                    origin = self._clean_location(origin_raw)
                                    f_date = (
                                        s_match.group(1).replace(".", "").strip()
                                        if s_match.group(1)
                                        else ""
                                    )
                                    dep_time = s_match.group(2)
                                    destination = self._clean_location(dest_raw)
                                    arr_time = ll_match.group(2)

                                    clase = cells[6] if len(cells) > 6 else "L"
                                    cabina = cells[7] if len(cells) > 7 else "Económica"

                                    flights.append(
                                        {
                                            "aerolinea": cells[0],
                                            "numero_vuelo": f_num.strip(),
                                            "origen": origin,
                                            "fecha_salida": f_date,
                                            "hora_salida": dep_time.strip(),
                                            "destino": destination,
                                            "hora_llegada": arr_time.strip(),
                                            "cabina": cabina,
                                            "clase": clase,
                                        }
                                    )
                            else:
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
                        except Exception as e:
                            logger.debug(f"Ignored error extracting flight: {e}")
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

    def _extract_amounts(self, text: str, html_text: str = "") -> list[dict[str, Any]]:
        """Extrae los importes (fare) encontrados en el texto.
        Busca la sección de totales y devuelve una lista de dicts con label y amount.
        """
        amounts: list[dict[str, Any]] = []
        soup = self._get_html_soup(text, html_text)
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
                        except Exception as e:
                            logger.debug("Ignored exception parsing amount: %s", e)
                            continue
        # Fallback al regex genérico sobre el texto plano
        amount_pattern = re.compile(r"([A-Za-z ]+?)\s*[:\s]?\s*\$?([\d,]+\.\d{2})")
        for label, value in amount_pattern.findall(text):
            try:
                amount = Decimal(value.replace(",", ""))
            except Exception as e:
                logger.debug("Ignored exception parsing fallback amount: %s", e)
                continue
            amounts.append({"label": label.strip(), "amount": amount})
        return amounts

    # Métodos auxiliares heredados de BaseTicketParser pueden ser usados directamente

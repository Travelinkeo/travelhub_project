import logging
import re

from apps.automation.parsers.base_parser import BaseTicketParser, ParsedTicketData

logger = logging.getLogger(__name__)


class AmadeusParser(BaseTicketParser):
    """Parser for Amadeus Electronic Ticket Receipts.
    Identified by 'Electronic Ticket Receipt' and 'CheckMyTrip' markers.
    """

    def can_parse(self, text: str) -> bool:
        """Check if text looks like an Amadeus ticket."""
        purified = self.purify_text_for_detection(text)

        # Evitar colisión con KIUSYS
        if "KIUSYS" in purified or "KIU SYSTEM" in purified or "KIU GDS" in purified:
            return False

        has_checkmytrip = "CHECKMYTRIP" in purified
        has_amadeus = "AMADEUS" in purified
        has_elec_tkt = "ELECTRONIC TICKET RECEIPT" in purified or "E-TICKET RECEIPT" in purified
        has_booking_ref = "BOOKING REF" in purified

        return bool(has_checkmytrip or has_amadeus or (has_elec_tkt and has_booking_ref))

    def parse(self, text: str, html_text: str = "", pdf_path: str = None) -> ParsedTicketData:
        """Main parsing method with robust AI fallback."""
        # --- PHASE 1: REGEX PARSING (Nativo) ---
        pnr = self.extract_field(
            text,
            [
                r"Booking ref\s*?:\s*([A-Z0-9]{6})",
                r"Booking reference\s*?:\s*([A-Z0-9]{6})",
                r"Record Locator\s*([A-Z0-9]{6})",
                r"AMADEUS\s+RESERVATION\s+NUMBER[:\s]+([A-Z0-9]{6})",
                r"RESERVA[^\n]*?([A-Z0-9]{6})",
            ],
        )

        ticket_number = self.extract_field(
            text,
            [
                r"Ticket\s*(?:number)?\s*?:\s*(\d{3}[-\s]?\d{10})",
                r"Ticket\s*:\s*(\d{3}[-\s]?\d{10})",
                r"ETICKET\s*NBR[:\s]*(\d{3}[-\s]?\d{10})",
                r"(\d{13})",
            ],
        )
        if ticket_number != "No encontrado":
            ticket_number = re.sub(r"[-\s]", "", ticket_number)

        passenger_name = self._extract_passenger(text) or "No encontrado"
        issue_date = self.extract_field(
            text,
            [
                r"Date\s*:\s*(\d{2}\s?[A-Z]{3,}\s?\d{2,4})",
                r"Fecha\s*:\s*(\d{2}\s?[A-Z]{3,}\s?\d{2,4})",
                r"Issued\s*date\s*[:\s]+([^\n]+)",
            ],
        )

        # Extraer itinerario mediante regex para verificar si es necesario el refuerzo de IA
        flights = self._extract_itinerary(text)

        # --- PHASE 2: AI REINFORCEMENT (Deep Integrity) ---
        if (
            pnr == "No encontrado"
            or passenger_name == "No encontrado"
            or ticket_number == "No encontrado"
            or not flights
        ):
            logger.info("Amadeus Native Regex incomplete or empty flights. Triggering AI Reinforcement.")
            try:
                from apps.automation.parsers.ai_universal_parser import UniversalAIParser

                ai_parser = UniversalAIParser()
                ai_data = ai_parser.parse(text, pdf_path=pdf_path)

                if ai_data and "error" not in ai_data:
                    if ai_data.get("is_multi_pax"):
                        ai_data = ai_data["tickets"][0]

                    if pnr == "No encontrado":
                        pnr = ai_data.get("CODIGO_RESERVA") or pnr
                    if passenger_name == "No encontrado":
                        passenger_name = ai_data.get("NOMBRE_DEL_PASAJERO") or passenger_name
                    if ticket_number == "No encontrado":
                        ticket_number = ai_data.get("NUMERO_DE_BOLETO") or ticket_number

                    return ParsedTicketData(
                        source_system="AMADEUS",
                        pnr=pnr,
                        ticket_number=ticket_number,
                        passenger_name=passenger_name,
                        passenger_document=ai_data.get("CODIGO_IDENTIFICACION"),
                        issue_date=ai_data.get("FECHA_DE_EMISION") or issue_date,
                        flights=ai_data.get("itinerario") or ai_data.get("vuelos") or [],
                        fares={
                            "fare_amount": ai_data.get("TARIFA_IMPORTE"),
                            "total_amount": ai_data.get("TOTAL_IMPORTE"),
                            "currency": ai_data.get("TOTAL_MONEDA"),
                        },
                        es_remision=ai_data.get("es_remision", False),
                        raw_data=ai_data,
                    )
            except Exception as e:
                logger.error(f"Fallo en AI Reinforcement de Amadeus: {e}")

        return ParsedTicketData(
            source_system="AMADEUS",
            pnr=pnr,
            ticket_number=ticket_number,
            passenger_name=passenger_name,
            issue_date=issue_date,
            flights=flights,
            fares={},
            agency={},
            raw_data={"text_snippet": text[:500]},
        )

    def _extract_passenger(self, text: str) -> str | None:
        # Cleaner logic for passenger name
        patterns = [
            r"Traveler\s+(?:MR|MRS|MS|MISS)?\s*([^\n]+?)\s+(?:Agency|Ticket|Booking)",
            r"Name\s*:\s*([^\n]+)",
            r"-([A-Z\s]+?)\s+\d{3}-",  # Case from table rows
        ]
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                name = re.sub(r"\((?:ADT|CHD|INF)\)", "", name)
                name = re.sub(r"\b(?:MR|MRS|MS|MISS|MSTR)\b", "", name, flags=re.IGNORECASE)
                return name.strip()
        return None

    def _extract_itinerary(self, text: str) -> list[dict]:
        segments = []
        lines = text.splitlines()

        # Strategy A: Table-based Regex (Simple)
        for line in lines:
            # Match 1: IATA codes and 4-digit hours (e.g. CCS IST TK022 U 15MAR 1135 0620)
            # Match 2: Full cities and colon hours (e.g. CARACAS ISTANBUL TK0224 U 15Mar 11:35 06:20)
            match = re.search(
                r"([A-Z]{3,})\s+([A-Z]{3,})\s+([A-Z0-9]{4,6})\s+([A-Z])\s+(\d{1,2}[A-Za-z]{3})\s+(\d{2}:?\d{2})\s+(\d{2}:?\d{2})",
                line,
                re.IGNORECASE,
            )
            if match:
                origin = match.group(1).strip()
                segments.append(
                    {
                        "origen": origin,
                        "destino": match.group(2).strip(),
                        "numero_vuelo": match.group(3).replace(" ", ""),
                        "clase": match.group(4),
                        "fecha_salida": match.group(5),
                        "hora_salida": match.group(6),
                        "hora_llegada": match.group(7),
                        "aerolinea": match.group(3).strip()[:2],
                    }
                )

        if segments:
            return segments

        # Strategy B: Verbose Format (Departure/Arrival headers)
        current_flight = {}
        for i, line in enumerate(lines):
            line = line.strip()

            # Flight line before Departure: "Turkish Airlines TK 224"
            flight_match = re.search(r"([A-Z0-9]{2})\s?(\d{3,4})", line)
            if flight_match and "Departure" in (lines[i + 1] if i + 1 < len(lines) else ""):
                current_flight["numero_vuelo"] = flight_match.group(1) + flight_match.group(2)
                current_flight["aerolinea"] = flight_match.group(1)

            if line.startswith("Departure"):
                match = re.search(r"Departure\s+(\d{1,2}\s+[A-Za-z]+)\s+(\d{2}:\d{2})\s+(.+)", line)
                if match:
                    current_flight["fecha_salida"] = match.group(1)
                    current_flight["hora_salida"] = match.group(2)
                    current_flight["origen"] = match.group(3).strip()

            elif line.startswith("Arrival") and current_flight:
                match = re.search(r"Arrival\s+(\d{1,2}\s+[A-Za-z]+)\s+(\d{2}:\d{2})\s+(.+)", line)
                if match:
                    current_flight["hora_llegada"] = match.group(2)
                    current_flight["destino"] = match.group(3).strip()

            elif line.startswith("Class") and current_flight:
                match = re.search(r"Class\s+.*?\(([A-Z])\)", line)
                if match:
                    current_flight["clase"] = match.group(1)
                    segments.append(current_flight)
                    current_flight = {}

        # Strategy C: Raw Flight Line Detection (line-by-line layout)
        if not segments:
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                flight_match = re.match(r"([A-Z]{2})(\d{3,4})", line)
                if flight_match:
                    numero_vuelo = f"{flight_match.group(1)}{flight_match.group(2)}"
                    aerolinea = flight_match.group(1)
                    # Look backwards for destination and origin
                    dest = ""
                    orig = ""
                    j = i - 1
                    while j >= 0 and not lines[j].strip():
                        j -= 1
                    if j >= 0:
                        dest = lines[j].strip()
                    k = j - 1
                    while k >= 0 and not lines[k].strip():
                        k -= 1
                    if k >= 0:
                        orig = lines[k].strip()
                    # Next lines: class, date, departure time, arrival time
                    clase = lines[i + 1].strip() if i + 1 < len(lines) else ""
                    fecha = lines[i + 2].strip() if i + 2 < len(lines) else ""
                    hora_salida = lines[i + 3].strip() if i + 3 < len(lines) else ""
                    hora_llegada = lines[i + 4].strip() if i + 4 < len(lines) else ""
                    segments.append(
                        {
                            "origen": orig,
                            "destino": dest,
                            "numero_vuelo": numero_vuelo,
                            "clase": clase,
                            "fecha_salida": fecha,
                            "hora_salida": hora_salida,
                            "hora_llegada": hora_llegada,
                            "aerolinea": aerolinea,
                        }
                    )
                    i += 5
                else:
                    i += 1

        return segments

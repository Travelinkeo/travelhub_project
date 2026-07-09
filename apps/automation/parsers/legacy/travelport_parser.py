import logging
import re

from apps.automation.parsers.base_parser import BaseTicketParser, ParsedTicketData

logger = logging.getLogger(__name__)


class TravelportParser(BaseTicketParser):
    """
    Parser for Travelport (Galileo/Worldspan/Apollo) Smartpoint scripts and emails.
    Identified by 'Travelport', 'Galileo', 'Worldspan' or 'ViewTrip' markers.
    """

    def can_parse(self, text: str) -> bool:
        """Check if text looks like a Travelport ticket."""
        purified = self.purify_text_for_detection(text)
        has_brand = (
            "TRAVELPORT" in purified
            or "GALILEO" in purified
            or "WORLDSPAN" in purified
            or "APOLLO" in purified
            or "VIEWTRIP" in purified
        )
        has_elec = "ELECTRONIC TICKET RECEIPT" in purified or "E-TICKET RECEIPT" in purified
        return bool(has_brand or (has_elec and "VIEWTRIP" in purified))

    def parse(self, text: str, html_text: str = "", pdf_path: str = None) -> ParsedTicketData:
        """Main parsing method with robust AI fallback."""

        # --- PHASE 1: REGEX PARSING (Nativo) ---
        pnr = self.extract_field(
            text,
            [
                r"BOOKING REFERENCE\s*[:\s]*([A-Z0-9]{6})",
                r"RESERVATION CODE\s*[:\s]*([A-Z0-9]{6})",
                r"GALILEO REFERENCE\s*[:\s]*([A-Z0-9]{6})",
                r"WORLDSPAN REFERENCE\s*[:\s]*([A-Z0-9]{6})",
                r"VENDOR LOCATOR\s*[:\s]*([A-Z0-9]{6})",
            ],
        )

        ticket_number = self.extract_field(
            text,
            [
                r"TICKET\s*NUMBER\s*[:\s]*(\d{3}[-\s]?\d{10})",
                r"DOCUMENT\s*NUMBER\s*[:\s]*(\d{3}[-\s]?\d{10})",
                r"ETKT\s*(\d{13})",
            ],
        )
        if ticket_number != "No encontrado":
            ticket_number = re.sub(r"[-\s]", "", ticket_number)

        passenger_name = self.extract_passenger_name_robust(text)

        issue_date = self.extract_field(
            text,
            [
                r"ISSUED\s*DATE\s*[:\s]*(\d{2}\s?[A-Z]{3,}\s?\d{2,4})",
                r"DATE\s*OF\s*ISSUE\s*[:\s]*(\d{2}\s?[A-Z]{3,}\s?\d{2,4})",
            ],
        )

        # Extraer itinerario mediante regex para verificar si es necesario el refuerzo de IA
        flights = self._extract_itinerary(text)

        # --- PHASE 2: AI REINFORCEMENT (Deep Integrity) ---
        # Si faltan campos críticos o el PNR es 'No encontrado', o no hay vuelos, usamos IA.
        if (
            pnr == "No encontrado"
            or passenger_name == "No encontrado"
            or ticket_number == "No encontrado"
            or not flights
        ):
            logger.info(
                "Travelport Native Regex incomplete or empty flights. Triggering AI Reinforcement."
            )
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
                        source_system="TRAVELPORT",
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
                logger.error(f"Fallo en AI Reinforcement de Travelport: {e}")

        return ParsedTicketData(
            source_system="TRAVELPORT",
            pnr=pnr,
            ticket_number=ticket_number,
            passenger_name=passenger_name,
            issue_date=issue_date,
            flights=flights,
            fares={},
            agency={},
            raw_data={"text_snippet": text[:500]},
        )

    def _extract_itinerary(self, text: str) -> list[dict]:
        """
        Extrae itinerario de Travelport usando patrones comunes de Galileo/Worldspan.
        Ejemplo:
        1  LA 2415 Y 12MAY LIMCUZ HK1  0915 1035  *OP/LA2415
        """
        segments = []
        lines = text.splitlines()

        # Patrón estándar de tramo de GDS
        flight_pattern = re.compile(
            r"(?:\d+\s+)?"  # Index opcional (1 )
            r"([A-Z0-9]{2})\s*"  # Aerolinea (LA)
            r"(\d{1,4})\s*"  # Numero de vuelo (2415)
            r"([A-Z])?\s*"  # Clase (Y) opcional
            r"(\d{2}[A-Z]{3})\s+"  # Fecha (12MAY)
            r"(?:\d\s+)?"  # Día de semana opcional (4 )
            r"([A-Z]{3})\s*([A-Z]{3})\s+"  # Origen y Destino (LIMCUZ o LIM CUZ)
            r"([A-Z0-9]{2,3})\s+"  # Status (HK1)
            r"(\d{4}[A-Z]?)\s+"  # Salida (0915)
            r"(\d{4}[A-Z]?)"  # Llegada (1035)
        )

        for line in lines:
            line_upper = line.upper().strip()
            match = flight_pattern.search(line_upper)
            if match:
                airline = match.group(1)
                flight_no = match.group(2)
                clase = match.group(3)
                date = match.group(4)
                origin = match.group(5)
                destination = match.group(6)
                status = match.group(7)
                dep_time = match.group(8)
                arr_time = match.group(9)

                # Normalizar horas (0915 -> 09:15)
                def norm_h(h):
                    h = re.sub(r"[A-Z]", "", h)
                    if len(h) == 4:
                        return f"{h[:2]}:{h[2:]}"
                    return h

                segments.append(
                    {
                        "origen": origin,
                        "destino": destination,
                        "numero_vuelo": f"{airline}{flight_no}",
                        "clase": clase or "Y",
                        "fecha_salida": date,
                        "hora_salida": norm_h(dep_time),
                        "hora_llegada": norm_h(arr_time),
                        "aerolinea": airline,
                        "status": status,
                    }
                )

        # Fallback a otra estructura más descriptiva de Galileo
        if not segments:
            current_flight = {}
            for line in lines:
                line_upper = line.upper().strip()
                f_match = re.search(r"FLIGHT\s*:\s*([A-Z0-9]{2})\s*(\d{1,4})", line_upper)
                if f_match:
                    current_flight["numero_vuelo"] = f_match.group(1) + f_match.group(2)
                    current_flight["aerolinea"] = f_match.group(1)

                    c_match = re.search(r"CLASS\s*:\s*([A-Z])", line_upper)
                    if c_match:
                        current_flight["clase"] = c_match.group(1)

                    d_match = re.search(r"DATE\s*:\s*(\d{2}[A-Z]{3})", line_upper)
                    if d_match:
                        current_flight["fecha_salida"] = d_match.group(1)

                dep_match = re.search(r"DEP\s*:\s*([A-Z]{3})\s+(\d{2}:\d{2})", line_upper)
                if dep_match:
                    current_flight["origen"] = dep_match.group(1)
                    current_flight["hora_salida"] = dep_match.group(2)

                arr_match = re.search(r"ARR\s*:\s*([A-Z]{3})\s+(\d{2}:\d{2})", line_upper)
                if arr_match and current_flight:
                    current_flight["destino"] = arr_match.group(1)
                    current_flight["hora_llegada"] = arr_match.group(2)
                    segments.append(current_flight)
                    current_flight = {}

        return segments

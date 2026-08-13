"""
Parser determinístico especializado para boletos GDS Amadeus y recibos CheckMyTrip.
Inherits from BaseTicketParser.
"""

import logging
import re
from typing import Any

from .base_parser import BaseTicketParser, ParsedTicketData

logger = logging.getLogger(__name__)


class AmadeusParser(BaseTicketParser):
    """Parser determinístico para pasajes e itinerarios GDS Amadeus."""

    def __init__(self):
        """Inicializa identificadores del parser Amadeus."""
        super().__init__()
        self.source_system = "AMADEUS"

    def can_parse(self, text: str) -> bool:
        """
        Verifica si el texto corresponde a un boleto o itinerario Amadeus.
        """
        if not text:
            return False

        upper_text = text.upper()
        keywords = [
            "AMADEUS",
            "CHECKMYTRIP",
            "1A/ELECTRONIC TICKET",
            "AMADEUS ELECTRONIC TICKET RECEIPT",
            "AMADEUS BOOKING REFERENCE",
            "CHECKMYTRIP ELECTRONIC TICKET RECEIPT",
        ]
        if any(kw in upper_text for kw in keywords):
            return True

        # Patrón típico de PNR Amadeus con etiqueta explícita
        if re.search(r"BOOKING REF(?:ERENCE)?\s*:\s*[A-Z0-9]{6}", upper_text):
            return True

        return False

    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        """
        Extrae datos estructurados desde el texto de Amadeus.
        """
        if not text:
            return ParsedTicketData(
                source_system=self.source_system,
                pnr="No encontrado",
                ticket_number=None,
                passenger_name="No encontrado",
                issue_date="No encontrado",
                raw_data={"raw_text": ""},
            )

        # 1. PNR / Booking reference
        pnr = (
            self.extract_field(
                text,
                [
                    r"BOOKING REF(?:ERENCE)?\s*:\s*([A-Z0-9]{6})",
                    r"RLOC\s*:\s*([A-Z0-9]{6})",
                    r"RESERVA\s*:\s*([A-Z0-9]{6})",
                    r"PNR\s*:\s*([A-Z0-9]{6})",
                    r"AMADEUS\s+([A-Z0-9]{6})",
                ],
            )
            or "No encontrado"
        )

        # 2. Número de Boleto (13 dígitos, prefijo opcional)
        ticket_number = self.extract_field(
            text,
            [
                r"TICKET(?:/ETKT)?\s*(?:NUMBER|NO|Nº)?\s*:\s*([0-9]{3}[-\s]?[0-9]{10})",
                r"BOLETO(?:\s+ELECTRONICO)?\s*:\s*([0-9]{3}[-\s]?[0-9]{10})",
                r"ETKT\s*:\s*([0-9]{3}[-\s]?[0-9]{10})",
                r"(?:^|\s)([0-9]{3}[-\s][0-9]{10})(?:\s|$)",
            ],
        )

        # 3. Nombre del Pasajero (AP APELLIDO/NOMBRE)
        passenger_name = (
            self.extract_field(
                text,
                [
                    r"PASSENGER(?:\s+NAME)?\s*:\s*([A-Z\s\/]{3,40})",
                    r"PASAJERO\s*:\s*([A-Z\s\/]{3,40})",
                    r"NAME\s*:\s*([A-Z\s\/]{3,40})",
                    r"1\.1\s*([A-Z\/]+)",
                ],
            )
            or "No encontrado"
        )

        # 4. Fecha de emisión
        issue_date = (
            self.extract_field(
                text,
                [
                    r"DATE OF ISSUE\s*:\s*([0-9]{2}[A-Z]{3}[0-9]{2,4}|[0-9]{2}/[0-9]{2}/[0-9]{4})",
                    r"FECHA EMISION\s*:\s*([0-9]{2}[A-Z]{3}[0-9]{2,4}|[0-9]{2}/[0-9]{2}/[0-9]{4})",
                    r"ISSUE DATE\s*:\s*([0-9]{2}[A-Z]{3}[0-9]{2,4}|[0-9]{2}/[0-9]{2}/[0-9]{4})",
                ],
            )
            or "No encontrado"
        )

        # 5. Documento / FOID / RIF
        passenger_document = self.extract_field(
            text,
            [
                r"FOID\s*:\s*([A-Z0-9\-]+)",
                r"DOC(?:UMENTO)?\s*:\s*([A-Z0-9\-]+)",
                r"RIF\s*:\s*([JVEG0-9\-]+)",
            ],
        )

        # 6. Vuelos / Itinerarios
        flights = self._extract_flight_segments(text)

        # 7. Tarifas
        fares = self._extract_fares(text)

        return ParsedTicketData(
            source_system=self.source_system,
            pnr=pnr,
            ticket_number=ticket_number,
            passenger_name=passenger_name,
            issue_date=issue_date,
            passenger_document=passenger_document,
            flights=flights,
            fares=fares,
            agency={"name": "AMADEUS GDS"},
            raw_data={"raw_text": text},
        )

    def _extract_flight_segments(self, text: str) -> list[dict[str, Any]]:
        """Extrae segmentos de vuelo en formato Amadeus."""
        flights = []
        # Patrón Amadeus: 1 AV 046 Y 22MAY BOGMAD HK1 0700 2330
        flight_pattern = r"(?P<flight_num>[A-Z0-9]{2}\s*\d{2,4})\s+(?P<cabin>[A-Z])\s+(?P<date>\d{2}[A-Z]{3})\s+(?P<dep>[A-Z]{3})(?P<arr>[A-Z]{3})\s+(?P<status>[A-Z]{2}\d+)?\s*(?P<dep_time>\d{4})?\s*(?P<arr_time>\d{4})?"

        for match in re.finditer(flight_pattern, text):
            g = match.groupdict()
            flights.append(
                {
                    "numero_vuelo": g["flight_num"].replace(" ", ""),
                    "clase": g["cabin"],
                    "fecha_salida": g["date"],
                    "origen": {"ciudad": g["dep"], "pais": None},
                    "destino": {"ciudad": g["arr"], "pais": None},
                    "hora_salida": g.get("dep_time", "00:00"),
                    "hora_llegada": g.get("arr_time", "00:00"),
                    "estatus": g.get("status", "HK1"),
                }
            )
        return flights

    def _extract_fares(self, text: str) -> dict[str, Any]:
        """Extrae tarifas e impuestos del boleto."""
        fares = {}
        fare_amount = self.extract_field(text, [r"AIR FARE\s*:\s*([A-Z]{3})?\s*([0-9\.]+)"])
        total_amount = self.extract_field(text, [r"TOTAL\s*:\s*([A-Z]{3})?\s*([0-9\.]+)"])
        currency = self.extract_field(text, [r"CURRENCY\s*:\s*([A-Z]{3})"]) or "USD"

        if fare_amount:
            try:
                fares["fare_amount"] = float(fare_amount)
                fares["fare_currency"] = currency
            except ValueError:
                pass

        if total_amount:
            try:
                fares["total_amount"] = float(total_amount)
                fares["total_currency"] = currency
            except ValueError:
                pass

        return fares

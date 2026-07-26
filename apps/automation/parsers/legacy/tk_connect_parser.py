"""Parser refactorizado para boletos TK Connect (Turkish Airlines)"""

from apps.automation.parsers.base_parser import BaseTicketParser, ParsedTicketData


class TKConnectParser(BaseTicketParser):
    """Parser para boletos de Turkish Airlines (TK Connect)"""

    def can_parse(self, text: str) -> bool:
        """can_parse."""
        purified = self.purify_text_for_detection(text)
        return "IDENTIFICACIÓN DEL PEDIDO" in purified and (
            "TK CONNECT" in purified or "TURKISH AIRLINES" in purified
        )

    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        """parse."""
        try:
            from django.utils.module_loading import import_string

            parse_tk_connect_ticket = import_string(
                "core.tk_connect_parser.parse_tk_connect_ticket"
            )

            # Usar parser legacy y adaptar resultado
            legacy_data = parse_tk_connect_ticket(text)
        except (ImportError, AttributeError):
            # Si no existe el parser legacy, retornar datos básicos
            import re

            pnr_match = re.search(
                r"IDENTIFICACIÓN DEL PEDIDO[:\s]+([A-Z0-9]{6})", text, re.IGNORECASE
            )
            ticket_match = re.search(r"Número de boleto[:\s]+([0-9-]+)", text, re.IGNORECASE)
            passenger_match = re.search(r"Pasajero[:\s]+([A-Z\s]+)", text, re.IGNORECASE)

            legacy_data = {
                "pnr": pnr_match.group(1) if pnr_match else "No encontrado",
                "numero_boleto": ticket_match.group(1) if ticket_match else None,
                "pasajero": {
                    "nombre_completo": passenger_match.group(1).strip()
                    if passenger_match
                    else "No encontrado"
                },
                "fecha_creacion": "",
                "vuelos": [],
            }

        return ParsedTicketData(
            source_system="TK_CONNECT",
            pnr=legacy_data.get("pnr", "No encontrado"),
            ticket_number=legacy_data.get("numero_boleto"),
            passenger_name=legacy_data.get("pasajero", {}).get("nombre_completo", "No encontrado"),
            issue_date=legacy_data.get("fecha_creacion", ""),
            flights=legacy_data.get("vuelos", []),
            fares={},
            raw_data=legacy_data,
        )

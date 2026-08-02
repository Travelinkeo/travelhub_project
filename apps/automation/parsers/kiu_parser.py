import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from .base_parser import BaseTicketParser, ParsedTicketData

logger = logging.getLogger(__name__)


class KIUParser(BaseTicketParser):
    """Parser para boletos del sistema KIU"""

    def can_parse(self, text: str) -> bool:
        """Detecta si es un boleto KIU"""
        purified = self.purify_text_for_detection(text)
        if (
            "KIUSYS.COM" in purified
            or "PASSENGER ITINERARY RECEIPT" in purified
            or ("ISSUE AGENT/AGENTE EMISOR" in purified and "FROM/TO" in purified)
        ):
            return True
        # Avianca/STC e-ticket receipt format
        if (
            "RECIBO DE BOLETO ELECTRÓNICO" in purified or "RECIBO DE BOLETO ELECTRONICO" in purified
        ) and ("AVIANCA" in purified or "AEROVIAS DEL CONTINENTE" in purified):
            return True
        return False

    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        """Parsea boleto KIU"""

        # 0. Limpieza PREVIA
        if not text:
            text = ""
        text = re.sub(r"<[^>]+>", " ", text)

        # 0b. Texto vacío: no invocar IA; retornar DTO vacío
        if not text.strip():
            return ParsedTicketData(
                source_system="KIU",
                pnr="No encontrado",
                ticket_number="No encontrado",
                passenger_name="No encontrado",
                issue_date="No encontrado",
            )

        # Detectar Avianca/STC receipt format
        purified = self.purify_text_for_detection(text)
        if (
            "RECIBO DE BOLETO ELECTRÓNICO" in purified or "RECIBO DE BOLETO ELECTRONICO" in purified
        ) and ("AVIANCA" in purified or "AEROVIAS DEL CONTINENTE" in purified):
            return self._parse_avianca_receipt(text, html_text)

        # 1. Intentar parsear como líneas crudas primero
        raw_kiu_pattern = r"^\s*\d+\s+[A-Z0-9]{2}\d+\s+[A-Z]\s+\d{2}[A-Z]{3}"
        if re.search(raw_kiu_pattern, text, re.MULTILINE):
            return self._parse_raw_kiu_lines(text)

        # 2. Parseo estándar
        passenger_name = self._extract_passenger_name(text)
        pnr = self._extract_pnr(text)
        ticket_number = self._extract_ticket_number(text)
        issue_date = self._extract_issue_date(text)

        # Extraer montos y detectar reemisión
        amounts = self._extract_amounts(text)
        es_remision = amounts.get("es_remision", False)

        # --- AI REINFORCEMENT ---
        if (
            pnr == "No encontrado"
            or ticket_number == "No encontrado"
            or passenger_name == "No encontrado"
        ):
            from apps.automation.services.ai_engine import ai_engine
            from apps.common.services.data_healer import DataHealer
            from core.api import ResultadoParseoSchema

            logger.info("KIU Native Regex incomplete. Triggering AI Reinforcement.")
            ai_res = ai_engine.call_gemini(
                prompt=f"Analiza este boleto de KIU:\n{text}",
                response_schema=ResultadoParseoSchema,
                system_instruction="Eres el experto en KIU GDS. Busca el PNR (C1/XXXXXX), el número de boleto y el pasajero. Identifica si es remisión (letra 'A' en total o Neto > Total).",
            )

            try:
                validated_res = DataHealer.heal_and_validate(ResultadoParseoSchema, ai_res)
                ai_data = validated_res.dict()
                boletos = ai_data.get("boletos", [])
                if boletos:
                    b = boletos[0]
                    if pnr == "No encontrado":
                        pnr = b.get("codigo_reserva")
                    if passenger_name == "No encontrado":
                        passenger_name = b.get("nombre_pasajero")
                    if ticket_number == "No encontrado":
                        ticket_number = b.get("numero_boleto")
                    if not es_remision:
                        es_remision = b.get("es_remision", False)
                    # Enriquecer otros campos si es necesario
            except Exception as e:
                logger.error(f"Fallo en AI Reinforcement de KIU: {e}")

        try:
            flights = self._extract_flights(text, html_text, issue_date=issue_date)
        except Exception:
            logger.error("Error extrañendo vuelos KIU", exc_info=True)
            flights = []

        # HEURÍSTICA DE REPARACIÓN
        # Si el nombre es 'S BOLETO NRO' (error típico), intentar buscar otro nombre
        # o marcar como revisión.
        if "BOLETO NRO" in passenger_name:
            passenger_name = "PENDIENTE / REVISAR"  # Fallback

        # Calcular SOLO_NOMBRE (Nombre/s de pila sin títulos) para el saludo
        from apps.automation.parsers.ticket_parser import _get_solo_nombre_pasajero

        solo_nombre = _get_solo_nombre_pasajero(passenger_name)

        return ParsedTicketData(
            source_system="KIU",
            pnr=pnr,
            passenger_name=passenger_name,
            ticket_number=ticket_number,
            issue_date=issue_date,
            es_remision=es_remision,
            agency={
                "iata": self._extract_agency_iata(text),
                "nombre": self._extract_agency_name(text),
                "direccion": self._extract_agency_address(text),
            },
            flights=flights,
            fares=amounts,
            raw_data={
                "ItinerarioFinalLimpio": self._extract_itinerary_text(text),
                "SOLO_NOMBRE_PASAJERO": solo_nombre,
                "passenger_name": passenger_name,  # Redundancia para seguridad
            },
            passenger_document=self._extract_foid(text),
        )

    def _extract_foid(self, text: str) -> str:
        """Extrae el FOID (Documento de Identidad)"""
        return self.extract_field(
            text,
            [
                r"FOID\s*[:\s]*([A-Z0-9-]+)",
                r"DOCUMENTO\s*[:\s]*([A-Z0-9-]+)",
                r"ID\s*[:\s]*([0-9-]{6,})",
                r"CEDULA\s*[:\s]*([VNEJP]-?[0-9.]+)",
            ],
        )

    def _parse_raw_kiu_lines(self, text: str) -> ParsedTicketData:
        """Parsea líneas de itinerario crudo de KIU."""
        flights = []
        lines = text.splitlines()
        # Regex: 1 5R300 S 30NOV SU CCSPMV HK1 0800 0840
        pattern = r"^\s*\d+\s+([A-Z0-9]{2})(\d+)\s+([A-Z])\s+(\d{2}[A-Z]{3})\s+[A-Z]{2}\s+([A-Z]{3})([A-Z]{3})\s+[A-Z0-9]+\s+(\d{4})\s+(\d{4})"
        # Regex alternativo (Sabre/KIU): 1 AV 46 C 22MAY BOGMAD HK1 0700 2330
        # Origen y destino pegados (6 letras), sin bloque de status separado
        pattern_pegado = r"^\s*\d+\s+([A-Z0-9]{2})\s?(\d{2,4})\s+([A-Z])\s+(\d{2}[A-Z]{3})\s+([A-Z]{3})([A-Z]{3})\s+[A-Z0-9]+\s+(\d{4})\s+(\d{4})"

        for line in lines:
            match = re.search(pattern, line)
            if not match:
                match = re.search(pattern_pegado, line)
            if match:
                airline_code = match.group(1)
                flight_num = match.group(2)
                clase = match.group(3)
                date_str = match.group(4)
                origin = match.group(5)
                dest = match.group(6)
                dep_time = match.group(7)
                arr_time = match.group(8)

                # Formatear hora (0800 -> 08:00)
                dep_time_fmt = f"{dep_time[:2]}:{dep_time[2:]}"
                arr_time_fmt = f"{arr_time[:2]}:{arr_time[2:]}"

                flights.append(
                    {
                        "aerolinea": airline_code,
                        "numero_vuelo": flight_num,
                        "clase": clase,
                        "fecha_salida": date_str,
                        "origen": origin,
                        "destino": dest,
                        "hora_salida": dep_time_fmt,
                        "hora_llegada": arr_time_fmt,
                        "equipaje": "N/A",  # No disponible en línea cruda
                    }
                )

        return ParsedTicketData(
            source_system="KIU",
            pnr="MANUAL",
            passenger_name="MANUAL",
            ticket_number="N/A",
            issue_date="N/A",
            flights=flights,
            raw_data={"ItinerarioFinalLimpio": text},
        )

    def _parse_avianca_receipt(self, text: str, html_text: str = "") -> ParsedTicketData:
        """Parsea el formato de recibo electrónico Avianca/STC."""
        lines = text.splitlines()
        dep_time = arr_time = None
        for i, line in enumerate(lines):
            if re.match(r"^\s*Hora\s*$", line, re.IGNORECASE):
                if i + 1 < len(lines):
                    time_val = lines[i + 1].strip()
                    if re.match(r"^\d{2}:\d{2}$", time_val):
                        if dep_time is None:
                            dep_time = time_val
                        else:
                            arr_time = time_val

        passenger_name = self._extract_passenger_name(text)
        if passenger_name == "No encontrado":
            m = re.search(
                r"Preparado para\s+([A-ZÁÉÍÓÚÑ /,()\-.]+?)(?:\s*\[|$)",
                text,
                re.IGNORECASE | re.MULTILINE,
            )
            if m:
                passenger_name = m.group(1).strip()

        pnr = self.extract_field(
            text,
            [
                r"CÓDIGO DE RESERVACIÓN\s*:?\s*([A-Z0-9]{6})",
                r"CODIGO DE RESERVACION\s*:?\s*([A-Z0-9]{6})",
                r"RESERVATION CODE\s*:?\s*([A-Z0-9]{6})",
            ],
        )
        if pnr == "No encontrado":
            pnr = self._extract_pnr(text)

        ticket_number = self._extract_ticket_number(text)
        issue_date = self._extract_issue_date(text)
        # Extract document from [DOC] after passenger name
        foid_match = re.search(r"\[(\d{6,10})\]", text)
        foid = foid_match.group(1) if foid_match else "No encontrado"

        airline_pnr = self.extract_field(
            text,
            [
                r"Código de reservación de la aerolínea\s+([A-Z0-9]{6})",
                r"CÓDIGO DE RESERVACIÓN DE LA AEROLÍNEA\s+([A-Z0-9]{6})",
                r"CODIGO DE RESERVACION DE LA AEROLINEA\s+([A-Z0-9]{6})",
            ],
        )

        # Extract flights from the Avianca receipt format
        flights = []
        in_flight_section = False
        i = 0
        lines_len = len(lines)
        while i < lines_len:
            line = lines[i]
            ls = line.strip()
            if (
                "INFORMACION DE VUELO" in ls.upper()
                or "INFORMACIÓN DE VUELO" in ls.upper()
                or "FLIGHT INFORMATION" in ls.upper()
            ):
                in_flight_section = True
                i += 1
                continue
            if not in_flight_section or not ls:
                i += 1
                continue
            # Skip table headers
            if ls.upper() in (
                "FECHA",
                "AEROLÍNEA",
                "AEROLINEA",
                "SALIDA",
                "LLEGADA",
                "OTRAS NOTAS",
            ):
                i += 1
                continue

            # Look for date line: "05 ago 26" or "05 AGO 26"
            date_match = re.match(r"^(\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4})$", ls)
            if not date_match or i + 4 >= lines_len:
                i += 1
                continue

            flight_date = date_match.group(1)

            # Collect airline info (may span multiple lines until we hit a city with comma)
            j = i + 1
            while j < lines_len and not lines[j].strip():
                j += 1
            airline_parts = []
            while j < lines_len and "," not in lines[j]:
                airline_parts.append(lines[j].strip())
                j += 1
            full_airline_line = " ".join(airline_parts)

            # Next non-empty line = origin city
            while j < lines_len and not lines[j].strip():
                j += 1
            origin_line = lines[j].strip() if j < lines_len else ""

            # Next non-empty line = destination city
            j += 1
            while j < lines_len and not lines[j].strip():
                j += 1
            dest_line = lines[j].strip() if j < lines_len else ""

            # Parse airline code + flight number from anywhere in the collected parts
            flight_match = re.search(r"\b([A-Z]{2})\s*(\d{3,4})\b", full_airline_line)
            flight_code = flight_match.group(1) if flight_match else ""
            flight_num = flight_match.group(2) if flight_match else ""

            airline = self.normalize_airline_name(
                raw_name=full_airline_line,
                flight_code=flight_code + flight_num if flight_code and flight_num else "",
            )

            origen = re.sub(r",\s*.+$", "", origin_line).strip()
            destino = re.sub(r",\s*.+$", "", dest_line).strip()

            flights.append(
                {
                    "aerolinea": flight_code or airline,
                    "numero_vuelo": flight_num,
                    "fecha_salida": flight_date,
                    "origen": {"ciudad": origen, "pais": None},
                    "destino": {"ciudad": destino, "pais": None},
                    "hora_salida": dep_time or "00:00",
                    "hora_llegada": arr_time or "00:00",
                    "aerolinea_nombre": airline,
                    "clase": "",
                    "equipaje": "N/A",
                }
            )
            i = j

        solo_nombre = (
            self._get_solo_nombre(passenger_name)
            if hasattr(self, "_get_solo_nombre")
            else passenger_name.split("/")[-1].split()[0].title()
            if "/" in passenger_name
            else passenger_name.split()[0].title()
        )

        raw_data = {
            "ItinerarioFinalLimpio": "\n".join(
                f"{f.get('origen', {}).get('ciudad', '') if isinstance(f.get('origen'), dict) else f.get('origen', '')} -> {f.get('destino', {}).get('ciudad', '') if isinstance(f.get('destino'), dict) else f.get('destino', '')}"
                for f in flights
            ),
            "SOLO_NOMBRE_PASAJERO": solo_nombre,
            "airline_name": "AVIANCA",
            "passenger_name": passenger_name,
        }
        if airline_pnr and airline_pnr != "No encontrado":
            raw_data["airline_pnr"] = airline_pnr

        return ParsedTicketData(
            source_system="KIU",
            pnr=pnr,
            passenger_name=passenger_name,
            ticket_number=ticket_number,
            issue_date=issue_date,
            passenger_document=foid,
            flights=flights,
            fares={},
            agency={},
            raw_data=raw_data,
        )

    def _heuristic_extract_total_and_currency(self, text: str) -> tuple[Decimal, str]:
        """_heuristic_extract_total_and_currency."""
        # 1. Determinar Moneda Globalmente
        moneda = "USD"
        if re.search(r"\b(VES|BS\.?|BOLIVARES)\b", text, re.IGNORECASE):
            moneda = "VES"
        elif re.search(r"\b(EUR|EUROS)\b", text, re.IGNORECASE):
            moneda = "EUR"

        # 2. Buscar TODOS los posibles montos (patrón: dígitos + punto/coma + 2 decimales)
        # Excluimos años (2025) y números de boleto largos
        regex_montos = r"\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})\b|\b\d+[.,]\d{2}\b"

        candidatos = re.findall(regex_montos, text)
        valores = []

        for c in candidatos:
            try:
                # Limpieza y normalización de montos
                clean_c = c.replace(" ", "")
                # Detectar formato: 1.234,56 (EU/VE) vs 1,234.56 (US)
                if "," in clean_c and "." in clean_c:
                    if clean_c.rfind(",") > clean_c.rfind("."):  # Caso 1.234,56
                        clean_c = clean_c.replace(".", "").replace(",", ".")
                    else:  # Caso 1,234.56
                        clean_c = clean_c.replace(",", "")
                elif "," in clean_c:
                    # Caso 1234,56
                    clean_c = clean_c.replace(",", ".")

                valor = float(clean_c)

                # Filtros de Seguridad (Heurística)
                # Ignoramos años (ej: 2024, 2025) si aparecen como montos sueltos,
                # pero 2025.00 sí podría ser un monto.
                # Rango de validez: 10 < valor < 100,000,000
                if 10 < valor < 100000000:
                    valores.append(Decimal(str(valor)))
            except Exception as e:
                logger.debug(f"Error procesando candidato de monto '{c}': {e}")
                continue

        # El total a pagar suele ser el monto numérico más alto en el documento
        monto_total = max(valores) if valores else Decimal("0.00")

        return monto_total, moneda

    def _extract_amounts(self, text: str) -> dict[str, Any]:
        """_extract_amounts."""
        # 1. Estrategia Robusta: "Max Number Strategy"
        heur_total, heur_currency = self._heuristic_extract_total_and_currency(text)

        # 2. Extracción de Base e Impuestos (Intentamos mantener desglose si es posible)
        # Usamos regex específicos solo para 'Fare' o 'Base'
        raw_base = self.extract_field(
            text,
            [
                r"(?:AIR FARE|TARIFA|FARE)\s*[:\s]*([A-Z]{3}\s*[0-9,.]+)",
                r"NETO\s*[:\s]*([A-Z]{3}\s*[0-9,.]+)",
            ],
        )
        base_curr, base_amt = self.extract_currency_amount(raw_base)

        # Si la heurística falló (0.00), intentamos usar lo específico
        total_amt = heur_total
        currency = heur_currency

        if total_amt == 0 and base_amt:
            total_amt = base_amt  # Fallback parcial
            currency = base_curr or currency

        # 3. Cálculo de Impuestos (Diferencia)
        tax_amt = Decimal("0.00")
        if total_amt > 0 and base_amt and total_amt >= base_amt:
            tax_amt = total_amt - base_amt
        elif total_amt > 0 and not base_amt:
            # Si no hay base, asumimos que todo es base+impuestos,
            # pero para efectos contables podríamos estimar o dejar base=total (neto)
            base_amt = total_amt

        # 4. Búsqueda de IVA (YN) para desglose
        iva_amt = Decimal("0.00")
        iva_match = re.search(r"([0-9]{1,5}(?:[.,][0-9]{2})?)\s*(?:YN)", text)
        if iva_match:
            try:
                raw_iva = iva_match.group(1).replace(",", ".")  # Simple fix
                iva_amt = Decimal(raw_iva)
            except Exception as e:
                logger.warning(f" Error al convertir IVA '{raw_iva}': {e}")

        other_taxes = Decimal("0.00")
        if tax_amt >= iva_amt:
            other_taxes = tax_amt - iva_amt
        else:
            # Si la diferencia es menor al IVA detectado, algo anda mal, priorizamos el Total Heurístico
            tax_amt = iva_amt  # Asumimos al menos el IVA

        # 5. Detección de remisión (reemisión): NETO > TOTAL o indicador "A" en el total
        es_remision = False
        neto_raw = self.extract_field(
            text,
            [
                r"NETO\s*[:\s]*(?:(?:[A-Z]{3})\s*)?([0-9,.]+)",
                r"NET\s*[:\s]*(?:(?:[A-Z]{3})\s*)?([0-9,.]+)",
            ],
        )
        neto_curr, neto_amt = self.extract_currency_amount(neto_raw)
        # El total heurístico es el máximo de montos, lo que puede ser el NETO mismo.
        # Para detectar remisión comparamos NETO contra el TOTAL explícito cuando exista.
        total_explicit_raw = self.extract_field(
            text,
            [
                r"TOTAL\s*[:\s]*(?:(?:[A-Z]{3})\s*)?([0-9,.]+)",
                r"TOTAL\s+NETO\s*[:\s]*(?:(?:[A-Z]{3})\s*)?([0-9,.]+)",
            ],
        )
        _, total_explicit_amt = self.extract_currency_amount(total_explicit_raw)

        # Fallback numérico: los montos pueden venir sin moneda (ej: "TOTAL: 1000")
        def _parse_plain_amount(raw: str) -> Decimal | None:
            if not raw or raw == "No encontrado":
                return None
            m = re.search(r"([0-9][0-9,.]*)", raw)
            if not m:
                return None
            try:
                return Decimal(m.group(1).replace(",", ""))
            except (InvalidOperation, ValueError):
                return None

        if neto_amt is None:
            neto_amt = _parse_plain_amount(neto_raw)
        if total_explicit_amt is None:
            total_explicit_amt = _parse_plain_amount(total_explicit_raw)

        base_for_remision = total_explicit_amt if total_explicit_amt is not None else total_amt
        if neto_amt is not None and base_for_remision > 0 and neto_amt > base_for_remision:
            es_remision = True
        elif not es_remision and re.search(
            r"\bREEMISI[ÓO]N\b|\bRE-?EMISSION\b", text, re.IGNORECASE
        ):
            es_remision = True
        elif not es_remision:
            # Indicador KIU: total mostrado con letra 'A' (ej: "A 1000.00")
            if re.search(r"\b[A]\s+[0-9,.]+", text):
                es_remision = True

        return {
            "currency": currency,
            "fare_amount": str(base_amt) if base_amt else "0.00",
            "total_amount": str(total_amt),
            "tax_details": {
                "total_taxes": str(tax_amt),
                "iva_yn": str(iva_amt),
                "other_taxes": str(other_taxes),
            },
            "es_remision": es_remision,
        }

    def _extract_ticket_number(self, text: str) -> str:
        """Extrae el número de boleto"""
        patterns = [
            r"TICKET N[BR]O?\s*[:\s]*([0-9-]{8,})",
            r"TICKET NUMBER\s*[:\s]*([0-9-]{8,})",
            r"TKT\s*[:\s]*([0-9-]{8,})",
            r"E-TICKET\s*[:\s]*([0-9-]{8,})",
            r"BOLETO\s*[:\s]*([0-9-]{8,})",
            r"\b(\d{3}-?\d{10})\b",  # Formato estándar XXX-XXXXXXXXXX
        ]
        result = self.extract_field(text, patterns)
        if result == "No encontrado":
            return result
        digits = re.sub(r"[^0-9]", "", result)
        # KIU emite boletos de 10 dígitos sin placa de aerolínea; se completa con la placa 235 (Avianca/KIU)
        if len(digits) == 10:
            return f"235{digits}"
        return digits if digits else result

    def _extract_issue_date(self, text: str) -> str:
        """Extrae la fecha de emisión"""
        patterns = [
            r"(?:ISSUE DATE|FECHA DE EMISI[OÓ]N|DATE OF ISSUE)\s*[:\s]*(\d{1,2}\s+\w{3}\s+\d{2,4})",
            r"(?:ISSUED|EMITIDO)\s*[:\s]*(\d{1,2}\s+\w{3}\s+\d{2,4})",
            r"(?:ISSUE DATE|FECHA DE EMISI[OÓ]N)\s*[:\s]*\n\s*(\d{1,2}\s+\w{3}\s+\d{2,4})",  # Multiline explicitly
            r"(\d{2}[A-Z]{3}\d{2})",  # Formato compacto: 15JAN25
        ]
        return self.extract_field(text, patterns)

    def _extract_pnr(self, text: str) -> str:
        """Extrae el PNR con múltiples patrones"""
        # Patrón 1: C1/XXXXXX (formato más común en KIU)
        match = re.search(r"C1\s*/\s*([A-Z0-9]{6})", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Patrón 2: BOOKING REF seguido del código
        booking_ref = self.extract_field(
            text,
            [
                r"BOOKING REF\.?\s*[:\s]*([A-Z0-9]{6})",
                r"BOOKING REFERENCE\s*[:\s]*([A-Z0-9]{6})",
                r"PNR\s*[:\s]*([A-Z0-9]{6})",
                r"LOCALIZADOR\s*[:\s]*([A-Z0-9]{6})",
                r"C[OÓ]DIGO DE RESERVACI[OÓ]N\s*[:\s]*([A-Z0-9]{6})",
                r"CODIGO DE RESERVACION\s*[:\s]*([A-Z0-9]{6})",
                r"RESERVATION CODE\s*[:\s]*([A-Z0-9]{6})",
            ],
        )

        if booking_ref != "No encontrado":
            # Si encontró algo, extraer solo el código de 6 caracteres
            match = re.search(r"\b([A-Z0-9]{6})\b", booking_ref)
            if match:
                return match.group(1)
            return booking_ref

        return "No encontrado"

    def _extract_passenger_name(self, text: str) -> str:
        """Extrae el nombre del pasajero usando la estrategia robusta centralizada"""
        result = self.extract_passenger_name_robust(text)
        if result == "No encontrado" and text:
            # El texto del campo "nombre" puede contener ruido tipo "BOLETO NRO <num>".
            # No forzamos un valor inventado: devolvemos el valor limpio para que el flujo
            # superior lo marque como PENDIENTE / REVISAR.
            cleaned = self.clean_text(re.sub(r"<[^>]+>", " ", text))
            if "BOLETO NRO" in cleaned.upper():
                return cleaned
        return result

    def _extract_agency_iata(self, text: str) -> str:
        """_extract_agency_iata."""
        return self.extract_field(text, [r"IATA\s*[:\s]*([0-9]{8})"])

    def _extract_agency_name(self, text: str) -> str:
        """_extract_agency_name."""
        # PRIORIDAD: Capturar exactamente lo que sigue a ISSUE AGENT / AGENTE EMISOR
        # El usuario indica que este es el código de la agencia (ej: BLA005RSJ)
        # y NO la aerolínea. Usamos lógica de main (3).py.
        raw_agent = self.extract_field(
            text,
            [
                r"ISSUE AGENT/AGENTE EMISOR\s*[:\s]*(.+)",
                r"ISSUE AGENT\s*[:\s]*(.+)",
                r"AGENTE EMISOR\s*[:\s]*(.+)",
                r"OFFICE ID\s*[:\s]*(.+)",
            ],
        )

        if raw_agent and raw_agent != "No encontrado":
            # Limpieza: El usuario indica que es un código de 8-9 caracteres (Office ID)
            # Ej: MIAO08217
            # A veces el regex captura "MIAO08217 DORAL FLORIDA..."
            # Tomamos la primera palabra y verificamos si parece un ID.
            first_word = raw_agent.split()[0].replace(":", "").strip()
            if 6 <= len(first_word) <= 12 and re.match(r"^[A-Z0-9]+$", first_word):
                return first_word

            # Si no parece código, devolvemos la línea limpia (fallback)
            return raw_agent.split("\n")[0].strip()

        return "No encontrado"

    def _extract_agency_address(self, text: str) -> str:
        """_extract_agency_address."""
        # Rutaca specifics
        if "RUTACA" in text.upper():
            return "AV JESUS SOTO SECTOR AEROPUERTO EDIF TALLER MARES, CIUDAD BOLIVAR, VE"

        # Extraer dirección pero DETENERSE ante keywords o salto de linea doble
        # Usamos un patrón que capture hasta encontrar keywords de fin de bloque
        raw_addr = self.extract_field(
            text,
            [
                r"ADDRESS/DIRECCI[OÓ]N\s*[:\s]*([^\n]+)",
                r"ADDRESS\s*[:\s]*([^\n]+)",
                r"DIRECCI[OÓ]N\s*[:\s]*([^\n]+)",
                r"ADDRESS/DIRECCI[OÓ]N\s*[:\s]*\n\s*([^\n]+)",  # Multiline explicit check
            ],
        )

        if raw_addr == "No encontrado":
            return raw_addr

        # Limpieza adicional por si la linea es muy larga o contiene basura
        stop_tokens = ["RIF", "TICKET", "NAME", "TELEPHONE", "MAIL", "ISSUING"]
        upper_addr = raw_addr.upper()

        cutoff = len(raw_addr)
        for token in stop_tokens:
            idx = upper_addr.find(token)
            if idx != -1:
                cutoff = min(cutoff, idx)

        return raw_addr[:cutoff].strip(" :-,.")

    def _extract_airline(self, text: str, ticket_number: str = None) -> str:
        """Extrae el nombre de la aerolínea con limpieza avanzada y normalización"""

        # 1. Extracción Cruda
        raw = self.extract_field(
            text,
            [
                r"ISSUING AIRLINE/LINEA AEREA EMISORA\s*[:\s]*([A-Z0-9 ,.&-]{3,})",
                r"ISSUING AIRLINE\s*[:\s]*([A-Z0-9 ,.&-]{3,})",
                r"LINEA AEREA EMISORA\s*[:\s]*([A-Z0-9 ,.&-]{3,})",
                r"LINEA AEREA EMISORA\s*[:\s]*\n\s*([A-Z0-9 ,.&-]{3,})",  # Multiline explicit
                r"AEROLINEA\s*[:\s]*([A-Z0-9 ,.&-]{3,})",
            ],
        )

        # 2. Normalización usando Base de Datos (Prioridad Placa -> IATA -> Nombre)
        # Usamos la función robusta que ya implementamos en BaseTicketParser/airline_utils
        normalized = self.normalize_airline_name(raw, ticket_number=ticket_number)

        if normalized and normalized != "Aerolínea no identificada":
            return normalized

        # 3. Fallbacks Heurísticos (solo si la normalización falló o devolvió nombre crudo sin match)
        upper_text = text.upper()
        if "RUTACA" in upper_text:
            return "RUTACA AIRLINES"
        if "AVIOR" in upper_text:
            return "AVIOR AIRLINES"
        if "ESTELAR" in upper_text:
            return "AEROLINEAS ESTELAR"
        if "CONVIASA" in upper_text:
            return "CONVIASA"
        if "LASER" in upper_text:
            return "LASER AIRLINES"
        if "TURPIAL" in upper_text:
            return "TURPIAL AIRLINES"
        if "VENEZOLANA" in upper_text:
            return "VENEZOLANA"

        # Limpieza final del raw si todo falla
        if raw != "No encontrado":
            # Eliminar "AGENTE" y todo lo que viene después
            raw = re.sub(r"\s+AGENTE.*$", "", raw, flags=re.IGNORECASE)
            # Limpiar sufijos
            raw = re.sub(r"/[A-Z0-9]{2,3}\s*$", "", raw)
            return raw.strip()

        return "Aerolínea no identificada"

    def _extract_flights(
        self, text: str, html_text: str = "", issue_date: str = None
    ) -> list[dict[str, Any]]:
        """Extrae vuelos del itinerario KIU"""
        flights = []
        seen_flights = set()
        from datetime import datetime

        # Patrón ancla: VUELO + CLASE + FECHA (Ej: V01187 G 2FEB o ES 791 G 2FEB26)
        # Se permite espacio opcional en el número de vuelo (ej: "ES 791")
        # Fecha: \d{1,2}[A-Z]{3} captura dia y mes. Añadimos (?:\d{2})? para año opcional.
        anchor_pattern = r"([A-Z0-9]{2}\s?\d{3,4})\s+([A-Z])\s+(\d{1,2}[A-Z]{3}(?:\d{2})?)"

        # Intentar parsear el año de emisión para usarlo de base
        dt_issue = None
        current_year = datetime.now().year

        if issue_date:
            from dateutil import parser as date_parser

            try:
                # issue_date suele venir normalizado o crudo?
                # _extract_issue_date devuelve string, tratemos de parsearlo
                dt_issue = date_parser.parse(issue_date, fuzzy=True)
                current_year = dt_issue.year
            except Exception as e:
                logger.warning(
                    f"No se pudo parsear la fecha de emisión '{issue_date}' para base de año: {e}"
                )

        lines = text.splitlines()
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Buscar el ancla
            match = re.search(anchor_pattern, line)
            if match:
                logger.info(f"DEBUG: Found flight anchor in '{line}'")

                flight_num = match.group(1).replace(
                    " ", ""
                )  # Normalizar quitando espacios internos
                clase = match.group(2)
                date_raw = match.group(3)  # Ej: 02FEB o 02FEB26

                # Normalizar Fecha a YYYY-MM-DD
                # Usamos método interno para evitar problemas de importación con stale modules
                flight_date = self._parse_date_iso(
                    date_raw, reference_date=dt_issue, base_year=current_year
                )

                # Lo que está ANTES del ancla es el Origen
                # match.start() es donde empieza el vuelo
                origin_raw = line[: match.start()].strip()

                # Lo que está DESPUÉS del ancla
                rest_raw = line[match.end() :].strip()

                # Extraer horas del resto (Ej: 0850 0950 ...)
                # Buscamos dos bloques de 4 dígitos
                times_match = re.search(r"(\d{4})\s+(\d{4})", rest_raw)
                dep_fmt = "00:00"
                arr_fmt = "00:00"

                if times_match:
                    dep_time = times_match.group(1)
                    arr_time = times_match.group(2)
                    dep_fmt = f"{dep_time[:2]}:{dep_time[2:]}"
                    arr_fmt = f"{arr_time[:2]}:{arr_time[2:]}"

                # Aerolínea Normalizada por Código de Vuelo
                # Usamos el método de la clase base que ya consulta DB
                airline = self.normalize_airline_name(raw_name=None, flight_code=flight_num)

                # Si falló la normalización, intentar inferir del código IATA manual o default
                if airline == "Aerolínea no identificada":
                    code = flight_num[:2]
                    if code == "V0":
                        airline = "CONVIASA"
                    elif code == "9V":
                        airline = "AVIOR AIRLINES"
                    elif code == "ES":
                        airline = "AEROLINEAS ESTELAR"
                    elif code == "VE":
                        airline = "RUTACA AIRLINES"
                    elif code == "QL":
                        airline = "LASER AIRLINES"
                    elif code == "L5":
                        airline = "LASER AIRLINES"
                    elif code == "R7":
                        airline = "ASERCA"
                    elif code == "Q6":
                        airline = "VIO"
                    elif code == "T9":
                        airline = "TURPIAL AIRLINES"
                    elif code == "G6":
                        airline = "GLOBAL AIRLINES"
                    else:
                        airline = "Aerolínea desconocida (" + code + ")"

                # Equipaje (Formatos: 23K, 2PC, 2P, 1PC, NIL, etc)
                # (?i) para case-insensitive (nil/NIL)
                bag_match = re.search(r"(?i)(NIL|\d{1,2}K|\d{1,2}PC|\d{1,2}P)\b", rest_raw)

                if bag_match:
                    equipaje = bag_match.group(1).upper()
                    if equipaje == "NIL":
                        equipaje = "0PC"
                else:
                    # Fallback para webs de Estelar, Rutaca, Avior que no imprimen equipaje
                    # Por defecto asumimos 1 pieza (23kg)
                    airline_upper = airline.upper()
                    if any(x in airline_upper for x in ["ESTELAR", "RUTACA", "AVIOR"]):
                        equipaje = "1PC"
                    else:
                        equipaje = "N/A"

                # Destino: Buscar en la siguiente línea
                dest = "DESCONOCIDO"
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()

                    # Limpieza agresiva de ruido (ej: "MADRID /CIERRE CHECKIN...")
                    # Cortar en /, *, o palabras clave que indican fin del nombre de ciudad
                    clean_dest = next_line
                    split_chars = [
                        "/",
                        "*",
                        "CIERRE",
                        "CHECKIN",
                        "REQUERIR",
                        "APIS",
                        "OPERADO",
                        "EQUIPAJE",
                    ]
                    for char in split_chars:
                        if char in clean_dest:
                            clean_dest = clean_dest.split(char)[0]

                    clean_dest = clean_dest.strip()

                    # Validar formato de ciudad (letras, espacios, guiones, puntos)
                    # Permitir BOGOTA-EL DORADO (con guion)
                    if re.match(r"^[A-ZÁÉÍÓÚ \.-]+$", clean_dest) and len(clean_dest) >= 3:
                        if not any(kw in clean_dest for kw in ["NAME", "PNR", "TICKET", "TOTAL"]):
                            dest = clean_dest

                # Generar clave única para evitar duplicados (ej: si el PDF repite el itinerario)
                unique_key = f"{flight_num}-{date_raw}-{origin_raw}"

                # Verificar si ya existe este segmento
                if unique_key in seen_flights:
                    continue
                seen_flights.add(unique_key)

                flights.append(
                    {
                        "aerolinea": airline,
                        "numero_vuelo": flight_num,
                        "clase": clase,
                        "fecha_salida": flight_date,  # Fecha ISO
                        "fecha_original": date_raw,
                        "origen": origin_raw,
                        "destino": dest,
                        "hora_salida": dep_fmt,
                        "hora_llegada": arr_fmt,
                        "equipaje": equipaje,
                    }
                )

        return flights

    def _parse_date_iso(self, date_str: str, reference_date=None, base_year=None) -> str:
        """
        Versión interna de _parse_date_flexible para evitar problemas de importación.
        """
        import datetime as dt

        if not date_str:
            return ""
        date_upper = date_str.upper().strip()
        from apps.automation.parsers.normalization import GDS_MONTH_EN as month_map

        for es, en in month_map.items():
            date_upper = date_upper.replace(es, en)

        try:
            dt_obj = None
            if re.match(r"^\d{1,2}[A-Z]{3}\d{2}$", date_upper):  # 02FEB26
                dt_obj = dt.datetime.strptime(date_upper, "%d%b%y")
            elif re.match(r"^\d{1,2}[A-Z]{3}\d{4}$", date_upper):  # 02FEB2026
                dt_obj = dt.datetime.strptime(date_upper, "%d%b%Y")
            elif re.match(r"^\d{1,2}[A-Z]{3}$", date_upper):  # 02FEB
                year = base_year or dt.now().year
                if reference_date:
                    year = reference_date.year
                dt_obj = dt.datetime.strptime(date_upper + str(year), "%d%b%Y")

                if reference_date:
                    delta = (dt_obj - reference_date).days
                    if delta > 180:
                        dt_obj = dt_obj.replace(year=year - 1)
                    elif delta < -180:
                        dt_obj = dt_obj.replace(year=year + 1)

            if dt_obj:
                return dt_obj.strftime("%Y-%m-%d")
        except Exception as e:
            logger.debug(f"Error fatal parseando fecha ISO KIU '{date_str}': {e}")
        return date_str

    def _extract_itinerary_text(self, text: str) -> str:
        """_extract_itinerary_text."""
        # Extraer bloque de itinerario
        start_pattern = r"(FROM/TO|DESDE/HACIA)[\s/]+(FLIGHT|VUELO)"
        end_keywords = ["ENDORSEMENTS", "CONDICIONES", "FARE CALC", "TOUR CODE", "PAYMENT", "TOTAL"]

        lines = text.splitlines()
        itinerary_content = []
        capturing = False

        for line in lines:
            if not capturing and re.search(start_pattern, line.upper()):
                capturing = True
                continue

            if capturing:
                if any(keyword in line.upper() for keyword in end_keywords):
                    break
                if line.strip():
                    itinerary_content.append(line.strip())

        return "\n".join(itinerary_content)

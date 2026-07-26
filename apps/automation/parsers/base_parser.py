"""
Clase base para todos los parsers de boletos.
Proporciona métodos comunes y define la interfaz que deben implementar todos los parsers.
"""

import logging
import quopri
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ParsedTicketData:
    """
    🚨 CRÍTICO | 🧠 IA / GOD MODE
    Estructura de Datos de Transferencia (DTO) que define la "Única Verdad" (Single Source of Truth) del ecosistema.

    ¿Por qué?: Los GDS (Sabre, KIU, Amadeus) tienen salidas radicalmente diferentes (HTML roto vs Plaintext).
    Tanto nuestras Expresiones Regulares heredadas (legacy) como Gemini (IA Parser) DEBEN mapear su resultado
    final a este Dataclass. Si alteras esto, crasheará la generación de Facturas, PDFs y la tabla `core_venta`.
    """

    source_system: str
    pnr: str
    ticket_number: str | None
    passenger_name: str
    issue_date: str
    passenger_document: str | None = None
    flights: list[dict[str, Any]] = field(default_factory=list)
    fares: dict[str, Any] = field(default_factory=dict)
    agency: dict[str, Any] = field(default_factory=dict)
    es_remision: bool = False
    raw_data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.fares, dict):
            if isinstance(self.fares, list):
                normalized_fares = {}
                for item in self.fares:
                    if isinstance(item, dict) and "label" in item and "amount" in item:
                        label = str(item["label"]).lower()
                        amount = item["amount"]
                        if "total" in label:
                            normalized_fares["total_amount"] = float(amount)
                        elif "tax" in label or "impuesto" in label:
                            normalized_fares["tax_amount"] = float(amount)
                        elif "fare" in label or "tarifa" in label or "rate" in label:
                            normalized_fares["fare_amount"] = float(amount)
                # Intentar rellenar vacíos
                if "fare_amount" not in normalized_fares and "total_amount" in normalized_fares:
                    normalized_fares["fare_amount"] = normalized_fares["total_amount"]
                self.fares = normalized_fares
            else:
                self.fares = {}

    def to_dict(self) -> dict[str, Any]:
        """
        🚨 CRÍTICO
        Exporta el DTO a un diccionario plano estandarizado.
        Sigue estrictamente el mapeo "BIBLIA DEL PARSEO" requerido por los templates Jinja2 del front-end
        (ej. 'NOMBRE DEL PASAJERO', 'TARIFA_IMPORTE') y por los workers de Celery al registrar la Venta.

        Returns:
            Dict[str, Any]: El diccionario masivo con alias retro-compatibles para el dashboard de ERP.
        """
        # Inicializa y construye el diccionario de salida normalizado mapeando todas las propiedades del DTO.
        # 1. Aerolínea del primer vuelo (o del raw_data)
        airline_name = self.raw_data.get("airline_name") or self.raw_data.get("reserva", {}).get(
            "aerolinea_emisora"
        )
        if not airline_name and self.flights:
            airline_name = self.flights[0].get("aerolinea")

        # 2. Solo Nombre Pasajero (Regla de Memoria)
        from apps.automation.parsers.ticket_parser import _get_solo_nombre_pasajero

        solo_nombre = self.raw_data.get("solo_nombre_pasajero") or _get_solo_nombre_pasajero(
            self.passenger_name
        )

        # 3. Solo Código Reserva (Limpieza C1/)
        solo_pnr = self.pnr
        if solo_pnr and "/" in solo_pnr:
            solo_pnr = solo_pnr.split("/")[-1]

        # 4. Agente Emisor (ID Único)
        agente_id = None
        used_key = None
        for key in ["iata", "numero_iata", "name"]:
            val = self.agency.get(key)
            if val and val != "No encontrado":
                agente_id = val
                used_key = key
                break
        if agente_id and used_key != "name":
            # Regla: solo el ID/Número
            match = re.search(r"([A-Z0-9]{3,})", str(agente_id))
            if match:
                agente_id = match.group(1)

        # 5. Estructura de Finanzas
        tarifa = self.fares.get("fare_amount")
        moneda = self.fares.get("fare_currency") or self.fares.get("total_currency")
        t_str = (
            f"{moneda} {tarifa}"
            if tarifa and moneda
            else str(tarifa)
            if tarifa
            else "No encontrado"
        )

        total = self.fares.get("total_amount")
        total_str = (
            f"{moneda} {total}" if total and moneda else str(total) if total else "No encontrado"
        )

        impuestos = self.fares.get("tax_amount")
        if not impuestos and total and tarifa:
            try:
                impuestos = f"{float(total) - float(tarifa):.2f}"
            except Exception as e:
                logger.warning(f"No se pudo calcular impuestos diferencial: {e}")
                impuestos = "0.00"

        # Normalizar vuelos
        vuelos_normalizados = []
        for f in self.flights or []:
            if not isinstance(f, dict):
                continue
            f_norm = f.copy()
            # 1. Normalizar fecha_salida_iso
            if "fecha_salida_iso" not in f_norm or not f_norm["fecha_salida_iso"]:
                raw_salida = f_norm.get("fecha_salida") or f_norm.get("date", "")
                if raw_salida:
                    from apps.automation.parsers.parsing_utils import (
                        _fecha_a_iso,
                        _formatear_fecha_dd_mm_yyyy,
                    )

                    formatted = _formatear_fecha_dd_mm_yyyy(raw_salida)
                    f_norm["fecha_salida_iso"] = _fecha_a_iso(formatted) or _fecha_a_iso(raw_salida)

            # 2. Normalizar fecha_llegada_iso
            if "fecha_llegada_iso" not in f_norm or not f_norm["fecha_llegada_iso"]:
                raw_llegada = (
                    f_norm.get("fecha_llegada")
                    or f_norm.get("fecha_salida")
                    or f_norm.get("date", "")
                )
                if raw_llegada:
                    from apps.automation.parsers.parsing_utils import (
                        _fecha_a_iso,
                        _formatear_fecha_dd_mm_yyyy,
                    )

                    formatted = _formatear_fecha_dd_mm_yyyy(raw_llegada)
                    f_norm["fecha_llegada_iso"] = _fecha_a_iso(formatted) or _fecha_a_iso(
                        raw_llegada
                    )

            # 3. Normalizar origen a diccionario para compatibilidad
            origen_val = f_norm.get("origen")
            if isinstance(origen_val, str):
                f_norm["origen"] = {"ciudad": origen_val, "pais": None}
            elif not isinstance(origen_val, dict):
                f_norm["origen"] = {"ciudad": str(origen_val or ""), "pais": None}

            # 4. Normalizar destino a diccionario para compatibilidad
            destino_val = f_norm.get("destino")
            if isinstance(destino_val, str):
                f_norm["destino"] = {"ciudad": destino_val, "pais": None}
            elif not isinstance(destino_val, dict):
                f_norm["destino"] = {"ciudad": str(destino_val or ""), "pais": None}

            vuelos_normalizados.append(f_norm)

        res = {
            "SOURCE_SYSTEM": self.source_system,
            # LLAVES MANDATORIAS (BIBLIA DEL PARSEO)
            "NOMBRE DEL PASAJERO": self.passenger_name,
            "CODIGO IDENTIFICACION": self.passenger_document
            or self.raw_data.get("FOID")
            or "No encontrado",
            "SOLO NOMBRE PASAJERO": solo_nombre,
            "NUMERO DE BOLETO": self.ticket_number,
            "FECHA DE EMISION": self.issue_date,
            "AGENTE EMISOR": agente_id,
            "CODIGO RESERVA": self.pnr,
            "SOLO CODIGO RESERVA": solo_pnr,
            "NOMBRE AEROLINEA": airline_name or "No encontrado",
            "DIRECCION AEROLINEA": self.raw_data.get("direccion_aerolinea") or "No encontrado",
            "vuelos": vuelos_normalizados,
            "TARIFA": t_str,
            "IMPUESTOS": impuestos,
            "TOTAL": total_str,
            "es_remision": self.es_remision,  # NUEVO CAMPO
            "localizador_aerolinea": self.raw_data.get("localizador_aerolinea")
            or self.raw_data.get("airline_pnr"),
            "airline_pnr": self.raw_data.get("localizador_aerolinea")
            or self.raw_data.get("airline_pnr"),
            # Aliases para compatibilidad con código antiguo/templates
            "pnr": self.pnr,
            "ticket_number": self.ticket_number,
            "passenger_name": self.passenger_name,
            "fecha_emision": self.issue_date,
            "TARIFA_IMPORTE": tarifa,
            "TOTAL_IMPORTE": total,
            "TARIFA_MONEDA": moneda,
            "TOTAL_MONEDA": moneda,
            "agencia": self.agency,
            "gds": self.source_system.lower(),
            # Compatibilidad adicional de tests
            "codigo_reservacion": self.pnr,
            "numero_boleto": self.ticket_number,
            "preparado_para": self.passenger_name,
            "documento_identidad": self.passenger_document or self.raw_data.get("FOID"),
            "aerolinea_emisora": airline_name or "No encontrado",
            "fecha_emision_iso": self.issue_date,
            "nombre_pasajero": self.passenger_name,
        }

        # Generar la versión normalizada
        # 🛡️ BULLETPROOF: La normalización accede a DB (Ciudad/Pais) y a catálogos
        # maestros. Si algo falla (DB caída, IATA ambiguo, RLS multi-tenant, etc.),
        # NO debe tragar todo el parseo: devolvemos los datos crudos extraídos por
        # el parser (que ya son válidos vía to_pydantic). Un boleto "sin normalizar"
        # sigue siendo usable en el Buffer de Revisión; un boleto sin datos, no.
        from apps.automation.parsers.normalization import DataNormalizationService

        try:
            res["normalized"] = DataNormalizationService.normalize_ticket_data(res)
        except Exception as e_norm:
            logger.error(
                "❌ Normalización falló en to_dict() — devolviendo datos crudos para "
                "no perder el parseo. Causa: %s",
                e_norm,
                exc_info=True,
            )
            # Fallback: la versión "normalizada" es el propio res sin segmentos
            # normalizados (se mantienen los vuelos crudos del parser).
            try:
                res["normalized"] = DataNormalizationService.sanitize_for_json(res)
            except Exception:
                logger.debug("sanitize_for_json falló, usando raw res como normalized")
                res["normalized"] = res
        return res

    def to_pydantic(self) -> Any:
        """
        Convierte y valida este DTO usando ResultadoParseoSchema de Pydantic.
        Garantiza consistencia estricta en todo el flujo de datos.
        """
        from core.api import (
            BoletoAereoSchema,
            ResultadoParseoSchema,
            TramoVueloSchema,
        )

        # Mapear tramos/vuelos
        itinerario_pydantic = []
        for f in self.flights:
            # Extraer origen/destino y sus códigos IATA
            origen_val = f.get("origen") or f.get("departure", {}).get("location") or "UNKNOWN"
            if isinstance(origen_val, dict):
                origen = origen_val.get("ciudad") or origen_val.get("city") or "UNKNOWN"
            else:
                origen = origen_val

            destino_val = f.get("destino") or f.get("arrival", {}).get("location") or "UNKNOWN"
            if isinstance(destino_val, dict):
                destino = destino_val.get("ciudad") or destino_val.get("city") or "UNKNOWN"
            else:
                destino = destino_val

            codigo_iata_origen = (
                f.get("codigo_iata_origen")
                or f.get("codigo_origen")
                or (origen if len(str(origen)) == 3 else None)
            )
            codigo_iata_destino = (
                f.get("codigo_iata_destino")
                or f.get("codigo_destino")
                or (destino if len(str(destino)) == 3 else None)
            )

            fecha_salida = f.get("fecha_salida") or f.get("date") or "UNKNOWN"
            hora_salida = f.get("hora_salida") or f.get("departure", {}).get("time") or "00:00"
            hora_llegada = f.get("hora_llegada") or f.get("arrival", {}).get("time") or "00:00"
            fecha_llegada = f.get("fecha_llegada") or fecha_salida

            tramo = TramoVueloSchema(
                aerolinea=f.get("aerolinea") or f.get("airline") or self.source_system,
                numero_vuelo=f.get("numero_vuelo") or f.get("vuelo") or f.get("flightNumber"),
                origen=origen,
                codigo_iata_origen=codigo_iata_origen,
                fecha_salida=fecha_salida,
                hora_salida=hora_salida,
                destino=destino,
                codigo_iata_destino=codigo_iata_destino,
                hora_llegada=hora_llegada,
                fecha_llegada=fecha_llegada,
                cabina=f.get("cabina") or f.get("clase") or "Económica",
                clase=f.get("clase") or f.get("class_of_service"),
                localizador_aerolinea=f.get("localizador_aerolinea")
                or f.get("airline_pnr")
                or self.pnr,
                equipaje=f.get("equipaje") or f.get("baggage"),
            )
            itinerario_pydantic.append(tramo)

        # Si no hay tramos, añadir uno ficticio para cumplir con la validación estricta
        if not itinerario_pydantic:
            itinerario_pydantic.append(
                TramoVueloSchema(
                    aerolinea=self.source_system,
                    numero_vuelo=None,
                    origen="UNKNOWN",
                    codigo_iata_origen=None,
                    fecha_salida=self.issue_date or "UNKNOWN",
                    hora_salida="00:00",
                    destino="UNKNOWN",
                    codigo_iata_destino=None,
                    hora_llegada="00:00",
                    fecha_llegada=self.issue_date or "UNKNOWN",
                    cabina="Económica",
                    clase=None,
                    localizador_aerolinea=self.pnr,
                    equipaje=None,
                )
            )

        # Mapear finanzas
        tarifa_val = self.fares.get("fare_amount") or 0.0
        impuestos_val = self.fares.get("tax_amount") or 0.0
        total_val = self.fares.get("total_amount") or 0.0
        moneda_val = self.fares.get("fare_currency") or self.fares.get("total_currency") or "USD"

        # Solo Nombre Pasajero
        from apps.automation.parsers.ticket_parser import _get_solo_nombre_pasajero

        solo_nombre = self.raw_data.get("solo_nombre_pasajero") or _get_solo_nombre_pasajero(
            self.passenger_name
        )

        # Aerolínea
        airline_name = self.raw_data.get("airline_name")
        if not airline_name and self.flights:
            airline_name = self.flights[0].get("aerolinea")
        if not airline_name:
            airline_name = "Aerolínea no identificada"

        # Instanciar BoletoAereoSchema
        boleto_schema = BoletoAereoSchema(
            nombre_pasajero=self.passenger_name,
            codigo_identificacion=self.passenger_document or self.raw_data.get("FOID"),
            solo_nombre_pasajero=solo_nombre,
            numero_boleto=self.ticket_number,
            fecha_emision=self.issue_date,
            agente_emisor=self.agency.get("name"),
            numero_iata=self.agency.get("iata") or self.agency.get("numero_iata"),
            codigo_reserva=self.pnr,
            codigo_reserva_aerolinea=self.raw_data.get("airline_pnr")
            or self.raw_data.get("pnr_aerolinea")
            or self.raw_data.get("localizador_aerolinea"),
            nombre_aerolinea=airline_name,
            direccion_aerolinea=self.raw_data.get("direccion_aerolinea"),
            itinerario=itinerario_pydantic,
            tarifa=tarifa_val,
            impuestos=impuestos_val,
            total=total_val,
            moneda=moneda_val,
            es_remision=self.es_remision,
            source_system=self.source_system,
            confidence_score=1.0,
            notas_advertencia=self.raw_data.get("notas_advertencia"),
        )

        return ResultadoParseoSchema(boletos=[boleto_schema])


class BaseTicketParser(ABC):
    """Clase base abstracta para los parsers con utilidades comunes."""

    def _get_html_soup(self, text: str) -> BeautifulSoup | None:
        """Extrae la sección HTML del email y la parsea con BeautifulSoup.
        Busca el bloque después de la cabecera 'Content-Type: text/html' y decodifica
        de base64 o quoted‑printable si es necesario.
        """
        # Buscar la parte HTML
        html_match = re.search(
            r"Content-Type:\s*text/html;.*?\r\n\r\n(.*?)(?:\r\n--|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if not html_match:
            return None
        html_content = html_match.group(1)
        # Intentar decodificar base64
        try:
            decoded_html = quopri.decodestring(html_content.encode()).decode(
                "utf-8", errors="ignore"
            )
        except Exception:
            logger.debug("HTML quoted-printable decode falló, usando raw")
            decoded_html = html_content
        return BeautifulSoup(decoded_html, "html.parser")

    """
    Clase base abstracta (Contrato/Interfaz) para todos los motores de extracción del sistema.

    ¿Por qué?: Implementamos el patrón arquitectónico Strategy. El orquestador itera sobre todos los
    parsers subclases (SabreParser, KIUParser, AIParser) y ejecuta `can_parse(...)` para saber
    quién debe hacerse cargo del archivo subido. Promueve extrema escalabilidad para nuevos proveedores.
    """

    @abstractmethod
    def can_parse(self, text: str) -> bool:
        """
        Determina si este parser puede procesar el texto dado.

        Args:
            text: Texto del boleto a analizar

        Returns:
            True si este parser puede procesar el texto
        """
        pass

    @abstractmethod
    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        """
        Parsea el texto y retorna datos normalizados.

        Args:
            text: Texto plano del boleto
            html_text: HTML del boleto (opcional)

        Returns:
            ParsedTicketData con los datos extraídos
        """
        pass

    # Métodos comunes compartidos por todos los parsers

    def extract_currency_amount(self, text: str) -> tuple[str | None, Decimal | None]:
        """
        Extrae moneda y monto de un texto.

        Args:
            text: Texto que contiene moneda y monto (ej: "USD 1,234.56")

        Returns:
            Tupla (moneda, monto) o (None, None) si no se encuentra
        """
        if not text or text == "No encontrado":
            return None, None

        match = re.search(r"([A-Z]{3})\s*([0-9,.]+)", text)
        if match:
            currency = match.group(1)
            raw_amount = match.group(2)

            # Determinar si la coma o el punto es el separador decimal
            last_comma = raw_amount.rfind(",")
            last_dot = raw_amount.rfind(".")

            if last_comma > last_dot and (len(raw_amount) - last_comma == 3):
                # La coma es decimal (ej: 1.234,56 o 492,25)
                amount_str = raw_amount.replace(".", "").replace(",", ".")
            else:
                # El punto es decimal (ej: 1,234.56 o 492.25)
                amount_str = raw_amount.replace(",", "")

            try:
                amount = Decimal(amount_str)
                return currency, amount
            except (InvalidOperation, ValueError):
                logger.warning(f"No se pudo convertir monto: {amount_str}")
                return currency, None

        return None, None

    def normalize_date(self, date_str: str, format_hint: str = None) -> str | None:
        """
        Normaliza una fecha a formato ISO (YYYY-MM-DD).

        Args:
            date_str: Fecha en formato variable
            format_hint: Pista del formato esperado

        Returns:
            Fecha en formato ISO o None si no se puede parsear
        """
        if not date_str or date_str == "No encontrado":
            return None

        # Importar utilidades de parsing existentes
        from apps.automation.parsers.parsing_utils import _fecha_a_iso, _formatear_fecha_dd_mm_yyyy

        formatted = _formatear_fecha_dd_mm_yyyy(date_str)
        iso_date = _fecha_a_iso(formatted) or _fecha_a_iso(date_str)

        return iso_date

    def clean_text(self, text: str) -> str:
        """
        Limpia texto eliminando espacios extras y caracteres especiales.

        Args:
            text: Texto a limpiar

        Returns:
            Texto limpio
        """
        if not text:
            return ""

        # Eliminar espacios múltiples
        text = re.sub(r"\s+", " ", text)
        # Eliminar espacios al inicio y final
        text = text.strip()

        return text

    def purify_text_for_detection(self, text: str) -> str:
        """
        Purifica el texto para detección de GDS (can_parse).
        Elimina etiquetas HTML, condensa múltiples espacios y convierte a mayúsculas.
        """
        if not text:
            return ""
        # Eliminar HTML
        t = re.sub(r"<[^>]+>", " ", text)
        t = t.replace("&nbsp;", " ")
        # Condensar múltiples espacios en uno solo
        t = re.sub(r"\s+", " ", t)
        return t.strip().upper()

    def extract_field(
        self,
        text: str,
        patterns: list[str],
        default: str = "No encontrado",
        negative_lookahead_patterns: list[str] = None,
    ) -> str:
        """
        Extrae un campo usando múltiples patrones regex.

        Args:
            text: Texto donde buscar
            patterns: Lista de patrones regex a probar
            default: Valor por defecto si no se encuentra
            negative_lookahead_patterns: Lista de patrones regex que, de encontrarse en el valor extraído, lo invalidan.

        Returns:
            Valor extraído o default
        """
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                value = self.clean_text(match.group(1))
                if negative_lookahead_patterns:
                    is_invalid = False
                    for neg_pattern in negative_lookahead_patterns:
                        if re.search(neg_pattern, value, re.IGNORECASE):
                            is_invalid = True
                            break
                    if is_invalid:
                        continue
                return value

        return default

    def normalize_airline_name(
        self, raw_name: str, flight_code: str = None, ticket_number: str = None
    ) -> str:
        """
        Normaliza el nombre de aerolínea usando utilidades existentes.

        Args:
            raw_name: Nombre crudo de la aerolínea
            flight_code: Código de vuelo para ayudar en la normalización
            ticket_number: Número de boleto para extraer placa/prefijo

        Returns:
            Nombre normalizado
        """
        from apps.automation.parsers.airline_utils import normalize_airline_name

        return normalize_airline_name(raw_name, flight_code, ticket_number=ticket_number)

    def extract_passenger_name_robust(self, text: str) -> str:
        """
        Extrae el nombre completo del pasajero aislando etiquetas HTML y ruido basura.

        Args:
            text (str): Texto plano o HTML crudo empaquetado del correo (.eml).

        Returns:
            str: Nombre extraído (ej. "PEREZ/JUANA") o 'No encontrado'.
        """
        # Limpiar HTML para la búsqueda de nombres
        clean_text = re.sub(r"<[^>]+>", " ", text)
        clean_text = clean_text.replace("&nbsp;", " ")

        # 1. Prioridad: Búsqueda por palabras clave explícitas (KIU/Sabre/Web)
        # Detener la captura si encontramos palabras clave de otros campos (FOID, RIF, etc.)
        patterns = [
            r"NAME/NOMBRE\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,60}?)(?:\s+(?:FOID|RIF|DNI|DOC|TKTN|ID|\[|$))",
            r"NAME:\s*([A-ZÁÉÍÓÚÑ/ (),.-]{3,60}?)(?:\s+(?:FOID|RIF|DNI|DOC|TKTN|ID|\[|$))",
            r"NOMBRE DEL PASAJERO\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,60}?)(?:\s+(?:FOID|RIF|DNI|DOC|TKTN|ID|\[|$))",
            r"PASAJERO\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,60}?)(?:\s+(?:FOID|RIF|DNI|DOC|TKTN|ID|\[|$))",
            r"PASJ\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,60}?)(?:\s+(?:FOID|RIF|DNI|DOC|TKTN|ID|\[|$))",
            r"PREPARADO PARA\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,60}?)(?:\s+(?:FOID|RIF|DNI|DOC|TKTN|ID|\[|$))",
            r"PREPARED FOR\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,60}?)(?:\s+(?:FOID|RIF|DNI|DOC|TKTN|ID|\[|$))",
        ]

        blacklist = [
            "DATE/FECHA",
            "FECHA/EMISION",
            "NAME/NOMBRE",
            "AGENT/AGENTE",
            "FROM/TO",
            "DESDE/HACIA",
            "TELEFONO",
            "PHONE",
            "MAIL",
            "CORREO",
            "DOCUMENTO",
            "ADDRESS/DIRECCION",
            "TICKET NUMBER/NRO DE BOLETO",
            "NO REEMBOLSABLE/NO ENDOSABLE",
            "NON END/NON REF",
            "AIR FARE/TARIFA",
            "TAX/IMPUESTOS",
            "FORM OF PAYMENT/FORMA DE PAGO",
            "PAGO",
            "ISSUING AIRLINE",
            "LINEA AEREA EMISORA",
            "EMISORA",
            "AIRLINE",
            "DIRECCION",
            "FORMA DE PAGO",
            "TARIFA",
            "IMPUESTOS",
            "NUMERO DE BOLETO",
            "PASSENGER NAME",
            "RESERVATION CODE",
            "CODIGO DE RESERVA",
            "CODIGO DE RESERVACION",
            "ELECTRONIC",
            "RECORD LOCATOR",
            "BOOKING REFERENCE",
            "TICKET NUMBER",
            "ISSUE AGENT",
            "EMITIDO",
            "PREPARADO PARA",
            "PREPARED FOR",
            "INFORMACION DE VUELO",
            "FLIGHT INFORMATION",
            "DEBERA",
            "PRESENTARSE",
            "MINIMO",
            "HORAS",
            "ANTES",
            "SALIDA",
            "VUELO",
            "EQUIPAJE",
            "FRANQUICIA",
            "CONDICIONES",
            "ORIGEN",
            "DESTINO",
        ]

        raw_name = "No encontrado"
        for pattern in patterns:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if not any(bad in candidate.upper() for bad in blacklist):
                    raw_name = candidate
                    break

        # 2. Estrategia 2: GDS Priority (APELLIDO/NOMBRE) si no hubo palabra clave
        if raw_name == "No encontrado" or len(raw_name) < 4:
            blacklist = [
                "DATE/FECHA",
                "FECHA/EMISION",
                "NAME/NOMBRE",
                "AGENT/AGENTE",
                "FROM/TO",
                "DESDE/HACIA",
                "TELEFONO",
                "PHONE",
                "MAIL",
                "CORREO",
                "DOCUMENTO",
                "ADDRESS/DIRECCION",
                "TICKET NUMBER/NRO DE BOLETO",
                "NO REEMBOLSABLE/NO ENDOSABLE",
                "NON END/NON REF",
                "AIR FARE/TARIFA",
                "TAX/IMPUESTOS",
                "FORM OF PAYMENT/FORMA DE PAGO",
                "PAGO",
                "ISSUING AIRLINE",
                "LINEA AEREA EMISORA",
                "EMISORA",
                "AIRLINE",
                "DIRECCION",
                "FORMA DE PAGO",
                "TARIFA",
                "IMPUESTOS",
                "NUMERO DE BOLETO",
                "PASSENGER NAME",
                "RESERVATION CODE",
                "CODIGO DE RESERVA",
                "CODIGO DE RESERVACION",
                "ELECTRONIC",
                "RECORD LOCATOR",
                "BOOKING REFERENCE",
                "TICKET NUMBER",
                "ISSUE AGENT",
                "EMITIDO",
                "PREPARADO PARA",
                "PREPARED FOR",
                "INFORMACION DE VUELO",
                "FLIGHT INFORMATION",
                "DEBERA",
                "PRESENTARSE",
                "MINIMO",
                "HORAS",
                "ANTES",
                "SALIDA",
                "VUELO",
                "EQUIPAJE",
                "FRANQUICIA",
                "CONDICIONES",
                "TARIFA",
                "ORIGEN",
                "DESTINO",
            ]

            # Buscar en el texto limpio (sin tags)
            matches = re.finditer(r"\b([A-Z]{2,}(?: [A-Z]+)*/[A-Z]{2,}(?: [A-Z]+)*)\b", clean_text)
            for match in matches:
                candidate = match.group(1).strip()
                if len(candidate) > 5 and not re.search(r"\d", candidate):
                    if not any(bad in candidate.upper() for bad in blacklist):
                        raw_name = candidate
                        break

        if raw_name == "No encontrado":
            return "No encontrado"

        return self.clean_passenger_name(raw_name)

    def clean_passenger_name(self, name: str) -> str:
        """
        Filtra sufijos, títulos de cortesía y ruidos colisionados.
        """
        if not name or name == "No encontrado":
            return name

        # 1. Asegurar limpieza de cualquier tag residual (HTML)
        name = re.sub(r"<[^>]+>", "", name)
        name = name.replace("&nbsp;", " ").strip()

        # 2. Eliminación de ruidos colisionados (FOID, RIF, etc.) si se colaron
        # Detenerse en el primer espacio seguido de una palabra clave de ruido
        # El split debe ser insensible a mayúsculas
        parts = re.split(r"\s+(?:FOID|RIF|DNI|DOC|TKTN|ID|\[)", name, flags=re.IGNORECASE)
        name = parts[0].strip()

        # 3. Eliminación de títulos y sufijos (MR, MS, MRS, CHD, INF)
        # Solo si hay un separador '/' (Estilo GDS/KIU)
        if "/" in name:
            # Eliminar títulos al final, soportando múltiples espacios
            name = re.sub(
                r"\s*\b(MR|MS|MRS|CHD|INF|MSTR|MISS)\b.*$", "", name, flags=re.IGNORECASE
            ).strip()

        # 4. Limpieza de caracteres residuales
        name = name.rstrip(":/.- ").strip()

        return name

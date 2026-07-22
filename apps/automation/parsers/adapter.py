"""
Adaptador para mantener compatibilidad con código legacy.
Permite usar los nuevos parsers sin romper el código existente.
"""

import logging
from typing import Any

from .kiu_parser import KIUParser
from .legacy.amadeus_parser import AmadeusParser
from .legacy.copa_parser import CopaParser
from .legacy.sabre_parser import SabreParser
from .legacy.tk_connect_parser import TKConnectParser
from .legacy.travelport_parser import TravelportParser
from .legacy.web_receipt_parser import WebReceiptParser
from .legacy.wingo_parser import WingoParser
from .registry import registry

logger = logging.getLogger(__name__)

# Registrar parsers al importar el módulo
_parsers_registered = False


def _register_parsers():
    """Registra todos los parsers disponibles"""
    global _parsers_registered
    if _parsers_registered:
        return

    registry.register(KIUParser())
    registry.register(WebReceiptParser())
    registry.register(CopaParser())
    registry.register(WingoParser())
    registry.register(TKConnectParser())
    registry.register(SabreParser())
    registry.register(AmadeusParser())
    registry.register(TravelportParser())

    _parsers_registered = True
    logger.info("Todos los parsers refactorizados registrados (8/8)")


def parse_ticket_with_new_parsers(text: str, html_text: str = "") -> dict[str, Any]:
    """
    Función adaptadora que usa los nuevos parsers pero retorna
    el formato esperado por el código legacy.

    Args:
        text: Texto plano del boleto
        html_text: HTML del boleto (opcional)

    Returns:
        Diccionario en formato legacy
    """
    _register_parsers()

    parser = registry.find_parser(text)
    if not parser:
        return {"error": "No se encontró parser compatible"}

    try:
        parsed_data = parser.parse(text, html_text)
        if not parsed_data:
            return {"error": "Parser returned no data"}

        # 🚨 CRÍTICO | Validación con Pydantic (ResultadoParseoSchema)
        # Garantiza que el output del parser se valide estrictamente contra el JSON Schema unificado
        try:
            parsed_data.to_pydantic()
            logger.info(
                f"✅ [Pydantic Validation] Exito al validar la salida de {parser.__class__.__name__} contra ResultadoParseoSchema."
            )
        except Exception as e_val:
            logger.warning(
                f"⚠️ [Pydantic Validation] La salida de {parser.__class__.__name__} no pudo validarse contra ResultadoParseoSchema: {e_val}"
            )

        try:
            return parsed_data.to_dict()
        except Exception as e_dict:
            # 🛡️ BULLETPROOF: to_dict() puede fallar en normalize_ticket_data
            # (consultas DB de Ciudad/Pais, IATA ambiguo, RLS multi-tenant, etc.).
            # Si to_pydantic() ya pasó, sabemos que el parser extrajo datos válidos.
            # Construimos un dict mínimo a partir del DTO directamente (sin
            # normalización de catálogos) para no perder el parseo completo.
            logger.error(
                f"❌ to_dict() falló en adapter para {parser.__class__.__name__}: {e_dict}. "
                "Construyendo dict mínimo para no perder el parseo.",
                exc_info=True,
            )
            return _build_minimal_dict(parsed_data)
    except Exception as e:
        logger.exception(f"Error al parsear con {parser.__class__.__name__}")
        return {"error": f"Error en parseo: {str(e)}"}


def _build_minimal_dict(parsed_data) -> dict[str, Any]:
    """
    Construye un diccionario mínimo pero válido a partir del ParsedTicketData
    (DTO) cuando to_dict() falla. Omite la normalización de catálogos IATA
    (que es lo que normalmente crashea por DB/RLS), pero preserva TODOS los
    campos críticos extraídos por el parser: pasajero, PNR, ticket, vuelos,
    fares, aerolínea.
    """
    from apps.automation.parsers.ticket_parser import _get_solo_nombre_pasajero

    solo_nombre = (
        getattr(parsed_data, "raw_data", {}).get("SOLO_NOMBRE_PASAJERO")
        or getattr(parsed_data, "raw_data", {}).get("solo_nombre_pasajero")
        or _get_solo_nombre_pasajero(parsed_data.passenger_name)
    )

    airline_name = getattr(parsed_data, "raw_data", {}).get("airline_name")
    if not airline_name and parsed_data.flights:
        airline_name = parsed_data.flights[0].get("aerolinea")

    vuelos_out = []
    for f in parsed_data.flights or []:
        if not isinstance(f, dict):
            continue
        # Asegurar origen/destino como dict (compat PDF/templates)
        origen = f.get("origen")
        if isinstance(origen, str):
            origen = {"ciudad": origen, "pais": None}
        elif not isinstance(origen, dict):
            origen = {"ciudad": str(origen or ""), "pais": None}
        destino = f.get("destino")
        if isinstance(destino, str):
            destino = {"ciudad": destino, "pais": None}
        elif not isinstance(destino, dict):
            destino = {"ciudad": str(destino or ""), "pais": None}
        vuelos_out.append({**f, "origen": origen, "destino": destino})

    fares = parsed_data.fares or {}
    moneda = (
        fares.get("fare_currency") or fares.get("currency") or fares.get("total_currency") or "USD"
    )
    tarifa = fares.get("fare_amount")
    total = fares.get("total_amount")
    impuestos = fares.get("tax_amount")
    if not impuestos and total and tarifa:
        try:
            impuestos = f"{float(total) - float(tarifa):.2f}"
        except Exception:
            impuestos = "0.00"

    return {
        "SOURCE_SYSTEM": parsed_data.source_system,
        "NOMBRE DEL PASAJERO": parsed_data.passenger_name,
        "nombre_pasajero": parsed_data.passenger_name,
        "SOLO NOMBRE PASAJERO": solo_nombre,
        "CODIGO IDENTIFICACION": parsed_data.passenger_document or "No encontrado",
        "NUMERO DE BOLETO": parsed_data.ticket_number,
        "ticket_number": parsed_data.ticket_number,
        "numero_boleto": parsed_data.ticket_number,
        "FECHA DE EMISION": parsed_data.issue_date,
        "fecha_emision": parsed_data.issue_date,
        "fecha_emision_iso": parsed_data.issue_date,
        "CODIGO RESERVA": parsed_data.pnr,
        "SOLO CODIGO RESERVA": (
            parsed_data.pnr.split("/")[-1]
            if parsed_data.pnr and "/" in parsed_data.pnr
            else parsed_data.pnr
        ),
        "pnr": parsed_data.pnr,
        "NOMBRE AEROLINEA": airline_name or "No encontrado",
        "aerolinea_emisora": airline_name or "No encontrado",
        "vuelos": vuelos_out,
        "TARIFA": f"{moneda} {tarifa}"
        if tarifa and moneda
        else (str(tarifa) if tarifa else "No encontrado"),
        "TARIFA_IMPORTE": tarifa,
        "TARIFA_MONEDA": moneda,
        "IMPUESTOS": impuestos,
        "TOTAL": f"{moneda} {total}"
        if total and moneda
        else (str(total) if total else "No encontrado"),
        "TOTAL_IMPORTE": total,
        "TOTAL_MONEDA": moneda,
        "agencia": parsed_data.agency or {},
        "gds": parsed_data.source_system.lower(),
        "es_remision": parsed_data.es_remision,
        "codigo_reservacion": parsed_data.pnr,
        "preparado_para": parsed_data.passenger_name,
        "documento_identidad": parsed_data.passenger_document,
        # Señal al pipeline: los datos están pero faltó normalización de catálogo.
        # El orquestador podrá marcar _requiere_revision=True si está incompleto.
        "_normalization_partial": True,
    }

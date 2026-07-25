"""Servicio de tax eligibility para la aplicación finance.
"""

import logging

logger = logging.getLogger(__name__)


# ELIMINADO: TaxRefundEngine - dependía de TaxRefundOpportunity (eliminado en refactor)


def es_itinerario_internacional(boleto) -> bool:
    """
    Determina si un boleto importado corresponde a un vuelo internacional.
    """
    if not boleto:
        return False

    # 1. Verificar datos_parseados estructurados
    datos = boleto.datos_parseados or {}
    vuelos = datos.get("vuelos", [])

    ciudades_nacionales = {
        "CARACAS",
        "MARACAIBO",
        "VALENCIA",
        "BARQUISIMETO",
        "PORLAMAR",
        "BARCELONA",
        "PUERTO ORDAZ",
        "MATURIN",
        "SAN CRISTOBAL",
        "EL VIGIA",
        "LAS PIEDRAS",
        "MERIDA",
        "CCS",
        "MAR",
        "VLN",
        "BRM",
        "PMV",
        "BLA",
        "PZO",
        "STD",
        "VIG",
        "LSP",
        "CUM",
        "MUN",
        "SOM",
        "VCR",
        "CXA",
    }

    if vuelos:
        for v in vuelos:
            dest = str(v.get("destino", "")).upper().strip()
            orig = str(v.get("origen", "")).upper().strip()

            # Si tiene destino u origen y no están en la lista nacional, es internacional
            if dest and not any(n in dest for n in ciudades_nacionales):
                return True
            if orig and not any(n in orig for n in ciudades_nacionales):
                return True

    # 2. Fallback al campo de texto de ruta_vuelo / itinerario
    ruta = str(boleto.ruta_vuelo or "").upper()
    if ruta:
        import re

        tokens = re.split(r"[\s\-/]+", ruta)
        for t in tokens:
            t = t.strip()
            # Si es un código IATA de 3 letras que no está en la lista de aeropuertos de Venezuela, asumimos internacional
            if len(t) == 3 and t.isalpha() and t not in ciudades_nacionales:
                return True

    return False

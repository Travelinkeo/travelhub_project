import io
import logging

import pypdf

logger = logging.getLogger(__name__)

PYPDF_AVAILABLE = True

PALABRAS_CLAVE_FUERTES = [
    "PASSENGER",
    "PASAJERO",
    "ITINERARY",
    "ITINERARIO",
    "BOLETO",
    "TICKET",
    "BILLETE",
    "E-TICKET",
    "ETICKET",
]

PALABRAS_CLAVE_SOPORTE = [
    "PNR",
    "LOCALIZADOR",
    "VUELO",
    "FLIGHT",
    "RESERVA",
    "RESERVACION",
    "CONFIRMACION",
    "CONFIRMED",
    "CONFIRMADO",
    "CLASE",
    "CLASS",
    "ASIENTO",
    "SEAT",
    "TARIFA",
    "FARE",
    "AEROLINEA",
    "AIRLINE",
    "SABRE",
    "KIU",
    "AMADEUS",
]


def es_pdf_boleto_valido(pdf_content, filename=""):
    """es_pdf_boleto_valido."""
    if not PYPDF_AVAILABLE:
        logger.info("pypdf no está disponible. Omitiendo filtro anti-ruido.")
        return True

    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_content))
        max_pages = min(len(reader.pages), 3)
        texto = ""
        for idx in range(max_pages):
            try:
                page_text = reader.pages[idx].extract_text()
                if page_text:
                    texto += page_text + "\n"
            except Exception as page_err:
                logger.debug(f"Error extrayendo texto de página {idx} de {filename}: {page_err}")

        if not texto:
            logger.info(
                f"PDF {filename} no contiene texto extraíble. Podría ser una imagen o escaneo."
            )
            return True

        texto_upper = texto.upper()
        tiene_fuerte = any(p in texto_upper for p in PALABRAS_CLAVE_FUERTES)
        coincidencias_soporte = sum(1 for p in PALABRAS_CLAVE_SOPORTE if p in texto_upper)

        es_valido = (tiene_fuerte and coincidencias_soporte >= 1) or (coincidencias_soporte >= 3)

        if not es_valido:
            logger.info(
                f"🚫 PDF '{filename}' descartado por filtro anti-ruido "
                f"(Fuerte: {tiene_fuerte}, Soporte: {coincidencias_soporte})"
            )
            return False

        logger.info(
            f"✅ PDF '{filename}' pasó el filtro anti-ruido "
            f"(Fuerte: {tiene_fuerte}, Soporte: {coincidencias_soporte})"
        )
        return True

    except Exception as e:
        logger.error(f"Error analizando PDF {filename} en filtro anti-ruido: {e}")
        return True

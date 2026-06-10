import logging
import re

import fitz

logger = logging.getLogger(__name__)


def extraer_datos_basicos(ruta_archivo):
    """
    Intenta extraer el localizador y un monto aproximado del PDF.
    Retorna un diccionario con datos o valores por defecto.
    """
    texto_completo = ""
    try:
        with fitz.open(ruta_archivo) as pdf:
            for page in pdf:
                t = page.get_text()
                if t:
                    texto_completo += t + "\n"

        # Lógica muy básica de extracción (Mejoraremos esto con los Parsers dedicados luego)
        # Buscar algo que parezca un Localizador (6 letras mayúsculas)
        match_loc = re.search(r"\b([A-Z2-9]{6})\b", texto_completo)
        localizador = match_loc.group(1) if match_loc else "GEN-001"

        # Retornamos datos simulados basados en lectura real para probar el flujo
        return {
            "texto_raw": texto_completo,
            "localizador": localizador,
            "pasajero": "PASAJERO IMPORTADO",  # Placeholder
            "total": 100.00,  # Monto base para prueba
        }
    except Exception as e:
        logger.error(f"Error leyendo PDF: {e}")
        return {"localizador": "ERROR", "total": 0}

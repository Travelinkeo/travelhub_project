# -*- coding: utf-8 -*-
"""
Servicio Orquestador de Parseo de Boletos v12 (CORREGIDO)

Este módulo actúa como un puente entre la aplicación Django y el 
parser principal del sistema (`core.ticket_parser`).

Su única responsabilidad es leer el contenido de un archivo y pasárselo
a la función `extract_data_from_text`, que contiene la lógica de 
detección de GDS.
"""

import logging
import fitz  # PyMuPDF
import email
from email import policy

# Importamos el ÚNICO punto de entrada para el parseo
from core.ticket_parser import extract_data_from_text

logger = logging.getLogger(__name__)

def _leer_contenido_del_archivo(archivo_subido) -> str:
    """
    Lee el contenido de un archivo subido (PDF, EML, o texto) y lo devuelve como string.
    """
    try:
        archivo_subido.seek(0)
        contenido_bytes = archivo_subido.read()
        archivo_subido.seek(0)

        # 1. Detección de PDF
        if contenido_bytes.startswith(b'%PDF'):
            logger.info("Detectado archivo PDF, extrayendo texto con PyMuPDF.")
            with fitz.open(stream=contenido_bytes, filetype="pdf") as doc:
                return "\n".join(page.get_text("text") for page in doc)

        # 2. Detección de EML
        # Un umbral simple: si contiene headers de email y es multipart.
        if b'Content-Type: multipart' in contenido_bytes[:2048] or b'Content-Type: text/plain' in contenido_bytes[:2048]:
            logger.info("Detectado archivo EML, extrayendo cuerpo del mensaje.")
            msg = email.message_from_bytes(contenido_bytes, policy=policy.default)
            
            plain_text_part = None
            html_part = None

            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain' and not plain_text_part:
                    plain_text_part = part
                if content_type == 'text/html' and not html_part:
                    html_part = part

            # Priorizar texto plano si está disponible
            target_part = plain_text_part if plain_text_part else html_part

            if target_part:
                payload = target_part.get_payload(decode=True)
                charset = target_part.get_content_charset() or 'utf-8'
                try:
                    return payload.decode(charset, errors='replace')
                except (UnicodeDecodeError, LookupError) as e:
                    logger.warning(f"No se pudo decodificar EML con charset {charset}, intentando con latin-1. Error: {e}")
                    return payload.decode('latin-1', errors='replace')
            
            logger.warning("No se encontró una parte 'text/plain' o 'text/html' en el EML, intentando decodificar el payload principal.")
            try:
                return contenido_bytes.decode('utf-8', errors='ignore')
            except UnicodeDecodeError:
                return contenido_bytes.decode('latin-1', errors='ignore')


        # 3. Fallback a texto plano
        logger.info("No se detectó PDF o EML, tratando como archivo de texto plano.")
        try:
            return contenido_bytes.decode('utf-8', errors='ignore')
        except UnicodeDecodeError:
            logger.warning("Fallo al decodificar como UTF-8, intentando con latin-1.")
            return contenido_bytes.decode('latin-1', errors='ignore')

    except Exception as e:
        logger.error(f"Error crítico al leer el contenido del archivo: {e}", exc_info=True)
        return ""


def orquestar_parseo_de_boleto(archivo_subido):
    """
    Orquesta el proceso de parseo de un boleto subido.
    
    1. Lee el contenido del archivo.
    2. Llama al orquestador principal `extract_data_from_text` que contiene la lógica de detección.
    3. Devuelve los datos parseados y un mensaje de estado.
    """
    contenido_texto = _leer_contenido_del_archivo(archivo_subido)
    
    if not contenido_texto:
        return None, "Error crítico: No se pudo leer el contenido del archivo."

    logger.info("Derivando al orquestador de parsers principal (extract_data_from_text).")
    
    # NOTA: El HTML no se extrae por separado en esta versión, se pasa el mismo texto.
    # La lógica de parseo de EML ahora devuelve el contenido de texto plano directamente.
    datos_parseados = extract_data_from_text(contenido_texto, html_text="")
    
    if not datos_parseados or datos_parseados.get("error"):
        error_msg = datos_parseados.get("error", "El parser no devolvió datos.")
        logger.error(f"Fallo en el parseo: {error_msg}")
        return None, f"Fallo en el parseo: {error_msg}"

    # --- INICIO DE LA MODIFICACIÓN --- 
    from decimal import Decimal, InvalidOperation

    # Usar el diccionario 'normalized' si existe, si no, el principal
    data_source = datos_parseados.get('normalized', datos_parseados)

    # Mapeo de campos con fallbacks para diferentes GDS (Sabre, KIU, etc.)
    fare_str = data_source.get('fare_amount') or data_source.get('TARIFA')
    total_str = data_source.get('total_amount') or data_source.get('TOTAL_IMPORTE') or data_source.get('TOTAL')

    try:
        if fare_str and total_str:
            tarifa_neta = Decimal(str(fare_str))
            tarifa_total = Decimal(str(total_str))
            
            # Forzar el cálculo de impuestos
            impuestos_calculados = tarifa_total - tarifa_neta
            
            # Actualizar el diccionario de datos parseados
            # Se prioriza la actualización en 'normalized' si existe
            if 'normalized' in datos_parseados:
                datos_parseados['normalized']['taxes_amount'] = f"{impuestos_calculados:.2f}"
            else:
                # Mapear a los campos de impuestos correspondientes (ej. 'IMPUESTOS' para KIU)
                datos_parseados['taxes_amount'] = f"{impuestos_calculados:.2f}"
                datos_parseados['IMPUESTOS'] = f"{impuestos_calculados:.2f}" # Asegurar compatibilidad

            logger.info(f"Cálculo de impuestos forzado: Total({tarifa_total}) - Neta({tarifa_neta}) = Impuestos({impuestos_calculados})")

    except (InvalidOperation, TypeError) as e:
        logger.warning(f"No se pudo forzar el cálculo de impuestos debido a un valor no decimal. Error: {e}")
    # --- FIN DE LA MODIFICACIÓN ---
        
    source_system = datos_parseados.get("SOURCE_SYSTEM", "DESCONOCIDO")
    mensaje = f"Parseo exitoso. GDS detectado: {source_system}."

    return datos_parseados, mensaje

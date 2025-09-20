# -*- coding: utf-8 -*-
"""
Sistema Inteligente de Parseo de Boletos para TravelHub (Versión Corregida y Robusta v6)

Este módulo proporciona una funcionalidad completa para leer, parsear y generar
PDFs a partir de boletos de avión en formato TXT o PDF.

Novedades v6:
- Se ha hecho el parser con expresiones regulares (fallback) mucho más robusto.
- Se han añadido verificaciones de seguridad para evitar errores "no such group"
  cuando un campo no se encuentra en el texto.
"""

import os
import re
import pathlib
import json
from datetime import datetime
import fitz  # PyMuPDF
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import google.generativeai as genai
from dotenv import load_dotenv

# --- CONFIGURACIÓN INICIAL ---
load_dotenv()

IA_CONFIGURADA = False
try:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro-latest",
            generation_config={"temperature": 0.1, "max_output_tokens": 8192, "response_mime_type": "application/json"},
        )
        IA_CONFIGURADA = True
        print("✅ Configuración de la IA de Gemini cargada correctamente.")
    else:
        print("⚠️ Advertencia: GOOGLE_API_KEY no encontrada. El parseo con IA estará deshabilitado.")
except Exception as e:
    print(f"❌ Error al configurar la IA de Gemini: {e}. El parseo con IA estará deshabilitado.")

# --- MÓDULO DE LECTURA DE ARCHIVOS ---

def leer_contenido_boleto(archivo_subido):
    """
    Lee el contenido de un archivo subido en Django (InMemoryUploadedFile).
    """
    print("📄 Leyendo boleto en memoria...")
    try:
        contenido_bytes = archivo_subido.read()
        archivo_subido.seek(0) # Rebobinar el archivo por si se necesita leer de nuevo

        # Identificar si es PDF por los "magic bytes"
        if contenido_bytes.startswith(b'%PDF'):
            doc = fitz.open(stream=contenido_bytes, filetype="pdf")
            texto_completo = ""
            for pagina in doc:
                texto_completo += pagina.get_text("text")
            doc.close()
            return texto_completo
        else: # Asumir que es texto plano
            return contenido_bytes.decode('utf-8')
    except Exception as e:
        print(f"  -> Error al leer el archivo en memoria: {e}")
        return None

# --- MÓDULO DE PARSEO CON IA (MÉTODO PRIMARIO) ---

def parsear_boleto_con_ia(texto_boleto):
    """
    (Método Principal) Envía el texto del boleto a Gemini y le pide que extraiga la información.
    """
    if not IA_CONFIGURADA:
        print("  -> Saltando parseo con IA (no configurada).")
        return None

    print("🧠 Enviando a la IA para parseo inteligente...")
    if not texto_boleto:
        return None

    prompt = """
    Eres un asistente experto para agencias de viajes, especializado en la extracción de datos de boletos de avión (ETKT) de GDS como Sabre.
    Tu tarea es leer el siguiente texto de un boleto y extraer la información clave en un formato JSON limpio y estructurado.

    Sigue estas reglas estrictamente:
    1.  El JSON debe tener la siguiente estructura exacta: {"pasajero": {}, "reserva": {}, "itinerario": {"vuelos": []}}.
    2.  En la sección "pasajero", extrae `nombre_completo` (formato APELLIDO/NOMBRE) y `documento_identidad`. El `documento_identidad` suele ser un código alfanumérico entre corchetes `[]` al lado del nombre.
    3.  En la sección "reserva", extrae `codigo_reservacion`, `numero_boleto`, `fecha_emision_iso` (en formato YYYY-MM-DD), `aerolinea_emisora` y `agente_emisor` (un objeto con `nombre` y `numero_iata`).
    4.  En la sección "itinerario", "vuelos" debe ser una lista de objetos, ordenados cronológicamente por fecha de salida.
    5.  Para cada vuelo, extrae: `fecha_salida` ("DD Mes YY"), `aerolinea`, `numero_vuelo` (el código de 2 letras y los números), `origen` (objeto con `ciudad` y `pais`), `destino` (objeto con `ciudad` y `pais`), `hora_salida` ("HH:MM"), `hora_llegada` ("HH:MM"), `terminal_salida`, `terminal_llegada`, `cabina`, `equipaje` y `codigo_reservacion_local`.
    6.  Si un campo no se encuentra en el texto, su valor en el JSON debe ser `null`. No inventes información.
    7.  La respuesta final debe ser SÓLO el objeto JSON, sin ningún texto adicional, explicaciones o ```json```.

    Texto del boleto a parsear:
    ---
    {texto_boleto}
    ---
    """
    
    try:
        response = model.generate_content(prompt.format(texto_boleto=texto_boleto))
        print("  -> IA respondió. Procesando JSON...")
        return json.loads(response.text)
    except Exception as e:
        print(f"  -> ❌ Error al procesar la respuesta de la IA: {e}")
        return None

# --- MÓDULO DE PARSEO CON REGEX (MÉTODO FALLBACK CORREGIDO) ---

def parsear_boleto_con_regex(texto_boleto):
    """
    (Método Fallback) Parsea un boleto usando expresiones regulares.
    Versión v6: Corregida para ser más robusta y evitar errores "no such group".
    """
    print("⚙️ Intentando parseo local con reglas (Fallback v6)...")
    if not texto_boleto:
        return None
    
    try:
        datos = {
            "pasajero": {"nombre_completo": None, "documento_identidad": None},
            "reserva": {"codigo_reservacion": None, "numero_boleto": None, "fecha_emision_iso": None, "aerolinea_emisora": None, "agente_emisor": {"nombre": None, "numero_iata": None}},
            "itinerario": {"vuelos": []}
        }
        
        # --- Extracción de Datos Principales (con verificaciones) ---
        pasajero_match = re.search(r"(?i)(?:Prepared For|Preparado para)\s*([\w\s/]+)(?:\[(.*?)\])?", texto_boleto)
        if pasajero_match:
            datos["pasajero"]["nombre_completo"] = " ".join(pasajero_match.group(1).strip().split())
            if pasajero_match.group(2):
                datos["pasajero"]["documento_identidad"] = pasajero_match.group(2).strip()
        
        reserva_match = re.search(r"(?i)(?:Reservation Code|CÓDIGO DE RESERVACIÓN)\s*([A-Z0-9]+)", texto_boleto)
        if reserva_match: datos["reserva"]["codigo_reservacion"] = reserva_match.group(1)

        boleto_match = re.search(r"(?i)(?:Ticket Number|NÚMERO DE BOLETO)\s*([0-9]+)", texto_boleto)
        if boleto_match: datos["reserva"]["numero_boleto"] = boleto_match.group(1)
        
        fecha_str_match = re.search(r"(?i)(?:Issue Date|FECHA DE EMISIÓN)\s*(\d{2}\s*\w{3}\s*\d{2})", texto_boleto)
        if fecha_str_match:
            try:
                # Lógica de conversión de fecha
                mes_map = {'ene': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'abr': 'Apr', 'may': 'May', 'jun': 'Jun', 'jul': 'Jul', 'ago': 'Aug', 'sep': 'Sep', 'oct': 'Oct', 'nov': 'Nov', 'dic': 'Dec'}
                fecha_str = fecha_str_match.group(1).lower()
                for k, v in mes_map.items():
                    fecha_str = fecha_str.replace(k, v)
                datos["reserva"]["fecha_emision_iso"] = datetime.strptime(fecha_str.replace(" ", ""), "%d%b%y").strftime("%Y-%m-%d")
            except ValueError:
                datos["reserva"]["fecha_emision_iso"] = fecha_str_match.group(1).strip()

        aerolinea_match = re.search(r"(?i)(?:Issuing Airline|AEROLÍN[E-Z]A EMISORA)\s*(.+)", texto_boleto)
        if aerolinea_match: datos["reserva"]["aerolinea_emisora"] = aerolinea_match.group(1).strip().splitlines()[0]

        agente_match = re.search(r"(?i)(?:Issuing Agent|AGENTE EMISOR)\s*([^/\n]+)", texto_boleto)
        if agente_match: datos["reserva"]["agente_emisor"]["nombre"] = agente_match.group(1).strip()
        
        iata_match = re.search(r"(?i)(?:IATA Number|NÚMERO IATA)\s*(\d+)", texto_boleto)
        if iata_match: datos["reserva"]["agente_emisor"]["numero_iata"] = iata_match.group(1)

        # --- Extracción de Itinerario Robusta ---
        bloques_texto = re.split(r'(?i)Esta no es una tarjeta de embarque|This is not a boarding pass', texto_boleto)
        
        for bloque in bloques_texto:
            if re.search(r"(?i)Salida:|Departure:|Travel Date", bloque):
                vuelo = {}
                
                fecha_match = re.search(r'(?i)(?:Salida:|Departure:|Travel Date)\s*(\d{2}\s*\w{3}\s*\d{2})', bloque)
                vuelo["fecha_salida"] = fecha_match.group(1).strip() if fecha_match else None
                
                vuelo_num_match = re.search(r'\b([A-Z0-9]{2}\s*\d{1,4})\b', bloque)
                vuelo["numero_vuelo"] = vuelo_num_match.group(1).strip() if vuelo_num_match else None

                aerolinea_match = re.search(r'(?i)(AIR\s*FRANCE|LAN\s*AIRLINES|PLUS\s*ULTRA|AEROVIAS\s*DEL\s*CONTINENTE|SATA\s*INTERNATIONAL|TURKISH\s*AIRLINES)', bloque)
                vuelo["aerolinea"] = aerolinea_match.group(1).strip() if aerolinea_match else None
                
                # Origen y Destino
                origen_match = re.search(r"(?is)(Salida|Departure|FROM)[\s,:]*([\w\s,]+?)\s*(?:Hora|Time)\s*(\d{2}:\d{2})", bloque)
                if origen_match:
                    vuelo["origen"] = {"ciudad": " ".join(origen_match.group(2).strip().replace('\n', ' ').split()), "pais": None}
                    vuelo["hora_salida"] = origen_match.group(3).strip()
                
                destino_match = re.search(r"(?is)(Llegada|Arrival|TO)[\s,:]*([\w\s,]+?)\s*(?:Hora|Time)\s*(\d{2}:\d{2})", bloque)
                if destino_match:
                    vuelo["destino"] = {"ciudad": " ".join(destino_match.group(2).strip().replace('\n', ' ').split()), "pais": None}
                    vuelo["hora_llegada"] = destino_match.group(3).strip()

                # Detalles adicionales
                terminal_s_match = re.search(r'(?is)(?:Salida|Departure|FROM).*?Terminal\s*([A-Z0-9\s]+)', bloque)
                vuelo["terminal_salida"] = terminal_s_match.group(1).strip().splitlines()[0] if terminal_s_match else None
                
                terminal_l_match = re.search(r'(?is)(?:Llegada|Arrival|TO).*?Terminal\s*([A-Z0-9\s]+)', bloque)
                vuelo["terminal_llegada"] = terminal_l_match.group(1).strip().splitlines()[0] if terminal_l_match else None

                pnr_local_match = re.search(r'(?i)(?:Airline Reservation Code|Código de reservación de la aerolínea)\s*([A-Z0-9]+)', bloque)
                vuelo["codigo_reservacion_local"] = pnr_local_match.group(1) if pnr_local_match else None

                cabina_match = re.search(r'(?i)Cabina\s*(TURISTA|PREMIUM TURISTA|ECONOMY)', bloque)
                vuelo["cabina"] = cabina_match.group(1) if cabina_match else None
                
                equipaje_match = re.search(r'(?i)(?:Baggage Allowance|Límite de equipaje)\s*([0-9A-Z]+)', bloque)
                vuelo["equipaje"] = equipaje_match.group(1) if equipaje_match else None

                if vuelo.get("fecha_salida"):
                     datos["itinerario"]["vuelos"].append(vuelo)

        print(f"  -> ✅ Parseo local con reglas encontró {len(datos['itinerario']['vuelos'])} segmentos.")
        return datos

    except Exception as e:
        print(f"  -> ❌ Error durante el parseo con reglas: {e}")
        return None

# --- MÓDULO DE ORQUESTACIÓN Y GENERACIÓN DE PDF ---

def orquestar_parseo_de_boleto(archivo_subido):
    """
    Función orquestadora principal. Devuelve una tupla (datos_parseados, mensaje_de_estado).
    """
    contenido = leer_contenido_boleto(archivo_subido)
    if not contenido:
        return None, "Fallo total: No se pudo leer el contenido del archivo."

    print("  -> Iniciando proceso de parseo...")
    
    # Intenta con IA primero
    datos_parseados = parsear_boleto_con_ia(contenido)
    
    # Si la IA falla, usa el fallback
    if not datos_parseados:
        print("  -> El parseo con IA falló o fue omitido. Intentando fallback local...")
        datos_parseados = parsear_boleto_con_regex(contenido)
        
    if datos_parseados:
        return datos_parseados, "Parseo exitoso."
    else:
        return None, "Fallo total: No se pudo parsear el boleto."

def generar_pdf_en_memoria(datos_boleto, ruta_plantilla):
    """
    Toma los datos JSON, los inyecta en la plantilla HTML y devuelve el PDF como bytes.
    """
    print(f"📄 Generando PDF en memoria...")
    try:
        directorio_plantilla = os.path.dirname(ruta_plantilla)
        nombre_plantilla = os.path.basename(ruta_plantilla)
        
        env = Environment(loader=FileSystemLoader(directorio_plantilla), autoescape=True)
        template = env.get_template(nombre_plantilla)
        
        html_renderizado = template.render(
            pasajero=datos_boleto.get('pasajero', {}), 
            reserva=datos_boleto.get('reserva', {}), 
            itinerario=datos_boleto.get('itinerario', {})
        )
        
        pdf_bytes = HTML(string=html_renderizado).write_pdf()
        print(f"  -> ✅ PDF generado con éxito en memoria.")
        return pdf_bytes
    except Exception as e:
        print(f"  -> ❌ Error al generar el PDF en memoria: {e}")
        return None


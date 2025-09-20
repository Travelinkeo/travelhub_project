# -*- coding: utf-8 -*-
"""
Sistema Inteligente de Parseo de Boletos para TravelHub (Versión Híbrida y Robusta v5)

Este módulo proporciona una funcionalidad completa para leer, parsear y generar
PDFs a partir de boletos de avión en formato TXT o PDF.

Utiliza una estrategia de dos pasos para máxima robustez:
1.  Intenta parsear los boletos usando la IA de Google (Gemini) para alta
    precisión y flexibilidad con cualquier formato.
2.  Si la IA falla (por error de conexión, API key no configurada, etc.),
    recurre a un parser local basado en expresiones regulares como fallback.

Este script está diseñado para ser integrado en el proyecto TravelHub de Django.
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
# Carga las variables de entorno (ideal para gestionar la API Key de forma segura)
load_dotenv()

IA_CONFIGURADA = False
try:
    # Intenta configurar la API de Gemini
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro-latest",
            # Configuración para respuestas más predecibles y en formato JSON
            generation_config={"temperature": 0.1, "max_output_tokens": 8192, "response_mime_type": "application/json"},
        )
        IA_CONFIGURADA = True
        print("✅ Configuración de la IA de Gemini cargada correctamente.")
    else:
        print("⚠️ Advertencia: GOOGLE_API_KEY no encontrada. El parseo con IA estará deshabilitado.")
except Exception as e:
    print(f"❌ Error al configurar la IA de Gemini: {e}. El parseo con IA estará deshabilitado.")

# --- MÓDULO DE LECTURA DE ARCHIVOS ---

def leer_contenido_boleto(ruta_archivo_o_bytes, es_bytes=False):
    """
    Lee el contenido de un boleto, ya sea desde una ruta de archivo o un objeto de bytes.
    Detecta si el contenido es de un TXT o PDF.
    """
    print(f"📄 Leyendo boleto...")
    try:
        if es_bytes:
            # Identificar si es PDF por los "magic bytes"
            if ruta_archivo_o_bytes.startswith(b'%PDF'):
                doc = fitz.open(stream=ruta_archivo_o_bytes, filetype="pdf")
            else: # Asumir que es texto plano
                return ruta_archivo_o_bytes.decode('utf-8')
        else: # Es una ruta de archivo
            if ruta_archivo_o_bytes.lower().endswith('.pdf'):
                doc = fitz.open(ruta_archivo_o_bytes)
            elif ruta_archivo_o_bytes.lower().endswith('.txt'):
                with open(ruta_archivo_o_bytes, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                print(f"  -> Error: Formato de archivo no soportado para '{ruta_archivo_o_bytes}'")
                return None

        texto_completo = ""
        for pagina in doc:
            texto_completo += pagina.get_text("text")
        doc.close()
        return texto_completo
    except Exception as e:
        print(f"  -> Error al leer el archivo: {e}")
        return None

# --- MÓDULO DE PARSEO CON IA (MÉTODO PRIMARIO) ---

def parsear_boleto_con_ia(texto_boleto):
    """
    (Método Principal) Envía el texto del boleto a Gemini y le pide que extraiga
    la información en un formato JSON estandarizado.
    """
    if not IA_CONFIGURADA:
        print("  -> Saltando parseo con IA (no configurada).")
        return None

    print("🧠 Enviando a la IA para parseo inteligente...")
    if not texto_boleto:
        return None

    # Prompt detallado y optimizado para obtener una salida JSON limpia.
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
        # La configuración "response_mime_type": "application/json" ayuda a que la salida sea directa
        print("  -> IA respondió. Procesando JSON...")
        return json.loads(response.text)
    except Exception as e:
        print(f"  -> ❌ Error al procesar la respuesta de la IA: {e}")
        return None

# --- MÓDULO DE PARSEO CON REGEX (MÉTODO FALLBACK) ---

def parsear_boleto_con_regex(texto_boleto):
    """
    (Método Fallback) Parsea un boleto usando expresiones regulares. Es menos flexible
    pero funciona sin conexión a internet. Versión v5.
    """
    print("⚙️ Intentando parseo local con reglas (Fallback v5)...")
    if not texto_boleto:
        return None
    
    try:
        datos = {
            "pasajero": {"nombre_completo": None, "documento_identidad": None},
            "reserva": {"codigo_reservacion": None, "numero_boleto": None, "fecha_emision_iso": None, "aerolinea_emisora": None, "agente_emisor": {"nombre": None, "numero_iata": None}},
            "itinerario": {"vuelos": []}
        }
        
        # --- Extracción de Datos Principales ---
        pasajero_match = re.search(r"(?i)(?:Prepared For|Preparado para)\s*([\w\s/]+)(?:\[(.*?)\])?", texto_boleto)
        if pasajero_match:
            datos["pasajero"]["nombre_completo"] = " ".join(pasajero_match.group(1).strip().split())
            datos["pasajero"]["documento_identidad"] = pasajero_match.group(2).strip() if pasajero_match.group(2) else None
        
        datos["reserva"]["codigo_reservacion"] = (re.search(r"(?i)(?:Reservation Code|CÓDIGO DE RESERVACIÓN)\s*([A-Z0-9]+)", texto_boleto) or [None, None])[1]
        datos["reserva"]["numero_boleto"] = (re.search(r"(?i)(?:Ticket Number|NÚMERO DE BOLETO)\s*([0-9]+)", texto_boleto) or [None, None])[1]
        
        fecha_str_match = re.search(r"(?i)(?:Issue Date|FECHA DE EMISIÓN)\s*(\d{2}\s*\w{3}\s*\d{2})", texto_boleto)
        if fecha_str_match:
            try:
                mes_map = {'ene': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'abr': 'Apr', 'may': 'May', 'jun': 'Jun', 'jul': 'Jul', 'ago': 'Aug', 'sep': 'Sep', 'oct': 'Oct', 'nov': 'Nov', 'dic': 'Dec'}
                fecha_str = fecha_str_match.group(1).lower()
                for k, v in mes_map.items():
                    fecha_str = fecha_str.replace(k, v)
                datos["reserva"]["fecha_emision_iso"] = datetime.strptime(fecha_str.replace(" ", ""), "%d%b%y").strftime("%Y-%m-%d")
            except ValueError:
                datos["reserva"]["fecha_emision_iso"] = fecha_str_match.group(1).strip()

        datos["reserva"]["aerolinea_emisora"] = (re.search(r"(?i)(?:Issuing Airline|AEROLÍNEA EMISORA)\s*(.+)", texto_boleto) or [None, None])[1]
        agente_match = re.search(r"(?i)(?:Issuing Agent|AGENTE EMISOR)\s*([^/\n]+)", texto_boleto)
        if agente_match:
            datos["reserva"]["agente_emisor"]["nombre"] = agente_match.group(1).strip()
        datos["reserva"]["agente_emisor"]["numero_iata"] = (re.search(r"(?i)(?:IATA Number|NÚMERO IATA)\s*(\d+)", texto_boleto) or [None, None])[1]

        # --- Extracción de Itinerario Robusta (v5) ---
        patron_segmento = r'(?is)(?P<fecha>\d{2}\s*\w{3}\s*\d{2}).*?(?P<aerolinea>AIR\s*FRANCE|LAN\s*AIRLINES|PLUS\s*ULTRA|AEROVIAS\s*DEL\s*CONTINENTE|SATA\s*INTERNATIONAL|TURKISH\s*AIRLINES.*?)(?P<vuelo_num>[A-Z]{2}\s*\d{1,4}).*?Salida|Departure|FROM:\s*(?P<origen_ciudad>[\w\s,]+?)(?:Hora|Time)\s*(?P<origen_hora>\d{2}:\d{2}).*?Llegada|Arrival|TO:\s*(?P<destino_ciudad>[\w\s,]+?)(?:Hora|Time)\s*(?P<destino_hora>\d{2}:\d{2})'
        
        # Lógica de búsqueda de bloques de vuelo mejorada
        bloques_texto = re.split(r'Esta no es una tarjeta de embarque|This is not a boarding pass', texto_boleto)
        
        for bloque in bloques_texto:
            if re.search(r"(?i)Salida:|Departure:|Travel Date", bloque):
                vuelo = {}
                vuelo["fecha_salida"] = (re.search(r'(?i)(?:Salida:|Departure:|Travel Date)\s*(\d{2}\s*\w{3}\s*\d{2})', bloque) or [None, None])[1]
                vuelo["numero_vuelo"] = (re.search(r'\b([A-Z0-9]{2}\s*\d{1,4})\b', bloque) or [None, None])[1]
                aerolinea_match = re.search(r'(?i)(AIR\s*FRANCE|LAN\s*AIRLINES|PLUS\s*ULTRA|AEROVIAS\s*DEL\s*CONTINENTE|SATA\s*INTERNATIONAL|TURKISH\s*AIRLINES)', bloque)
                vuelo["aerolinea"] = aerolinea_match.group(1).strip() if aerolinea_match else None
                
                # Origen y Destino
                origen_match = re.search(r"(?is)(Salida|Departure|FROM)\s*,\s*([\w\s,]+?)\s*(?:Hora|Time)\s*(\d{2}:\d{2})", bloque)
                if not origen_match:
                     origen_match = re.search(r"(?is)(?:SALIDA|DEPARTURE)\s*\n\s*([\w\s,]+?)\s*Hora\s*(\d{2}:\d{2})", bloque)

                destino_match = re.search(r"(?is)(Llegada|Arrival|TO)\s*,\s*([\w\s,]+?)\s*(?:Hora|Time)\s*(\d{2}:\d{2})", bloque)
                if not destino_match:
                     destino_match = re.search(r"(?is)(?:LLEGADA|ARRIVAL)\s*\n\s*([\w\s,]+?)\s*Hora\s*(\d{2}:\d{2})", bloque)

                if origen_match:
                    vuelo["origen"] = {"ciudad": " ".join(origen_match.group(2).strip().replace('\n', ' ').split()), "pais": None}
                    vuelo["hora_salida"] = origen_match.group(3).strip()
                if destino_match:
                    vuelo["destino"] = {"ciudad": " ".join(destino_match.group(2).strip().replace('\n', ' ').split()), "pais": None}
                    vuelo["hora_llegada"] = destino_match.group(3).strip()

                # Detalles adicionales
                vuelo["terminal_salida"] = (re.search(r'(?is)(?:Salida|Departure|FROM).*?Terminal\s*([A-Z0-9\s]+)', bloque) or [None, "N/A"])[1].strip()
                vuelo["terminal_llegada"] = (re.search(r'(?is)(?:Llegada|Arrival|TO).*?Terminal\s*([A-Z0-9\s]+)', bloque) or [None, "N/A"])[1].strip()
                vuelo["codigo_reservacion_local"] = (re.search(r'(?i)(?:Airline Reservation Code|Código de reservación de la aerolínea)\s*([A-Z0-9]+)', bloque) or [None, None])[1]
                vuelo["cabina"] = (re.search(r'(?i)Cabina\s*(TURISTA|PREMIUM TURISTA|ECONOMY)', bloque) or [None, None])[1]
                vuelo["equipaje"] = (re.search(r'(?i)(?:Baggage Allowance|Límite de equipaje)\s*([0-9A-Z]+)', bloque) or [None, None])[1]

                if vuelo.get("fecha_salida") and (vuelo.get("origen") or vuelo.get("destino")):
                     datos["itinerario"]["vuelos"].append(vuelo)


        print(f"  -> ✅ Parseo local con reglas encontró {len(datos['itinerario']['vuelos'])} segmentos.")
        return datos

    except Exception as e:
        print(f"  -> ❌ Error durante el parseo con reglas: {e}")
        return None

# --- MÓDULO DE ORQUESTACIÓN Y GENERACIÓN DE PDF ---

def procesar_y_generar_pdf(ruta_archivo_boleto, plantilla_html, ruta_salida_pdf):
    """
    Función principal que orquesta todo el proceso:
    1. Lee el archivo.
    2. Intenta parsear con IA.
    3. Si falla, intenta parsear con Regex.
    4. Si tiene éxito, genera el PDF.
    """
    contenido = leer_contenido_boleto(ruta_archivo_boleto)
    if not contenido:
        print(f"  -> ❌ FALLO LECTURA: No se pudo leer el contenido de: {ruta_archivo_boleto}")
        return False

    print("  -> Iniciando proceso de parseo...")
    
    # Intenta con IA primero
    datos_parseados = parsear_boleto_con_ia(contenido)
    
    # Si la IA falla, usa el fallback
    if not datos_parseados:
        print("  -> El parseo con IA falló o fue omitido. Intentando fallback local...")
        datos_parseados = parsear_boleto_con_regex(contenido)
        
    # Si tenemos datos, generamos el PDF
    if datos_parseados:
        generar_pdf_desde_plantilla(datos_parseados, plantilla_html, ruta_salida_pdf)
        return True
    else:
        print(f"  -> ❌ FALLO TOTAL: No se pudo parsear el boleto '{ruta_archivo_boleto}' ni con IA ni con reglas locales.")
        return False


# --- BLOQUE DE EJECUCIÓN DE PRUEBA ---
# Este bloque solo se ejecuta si corres el script directamente.
# Es ideal para probar la funcionalidad de forma aislada.

if __name__ == "__main__":
    print("🚀 Iniciando el Sistema de Parseo Híbrido de Boletos TravelHub 🚀")
    
    # Lista de archivos para la prueba
    archivos_de_prueba = [
        "0577327765921.txt",
        "0457325955129.txt",
        "Recibo de pasaje electrónico, 07 abril para JHONY ALBERTO QUINTERO RAMIREZ.pdf",
        "Recibo de pasaje electrónico, 19 marzo para ROSANGELA DIAZ SILVA.pdf",
        "Recibo de pasaje electrónico, 21 mayo para ANNE MARIE BELLO.pdf",
        "Recibo de pasaje electrónico, 27 mayo para JOSE ARMANDO ALEMAN MARICHALES.pdf",
        "Recibo de pasaje electrónico, 17 agosto para JIMMY ALEJANDRO ZULUAGA JABER.pdf"
    ]
    
    plantilla_path = "ticket_template_sabre.html"
    directorio_salida = "boletos_generados"
    pathlib.Path(directorio_salida).mkdir(exist_ok=True)

    for archivo in archivos_de_prueba:
        if not os.path.exists(archivo):
            print(f"\n  -> ⚠️  Archivo de prueba no encontrado, saltando: {archivo}")
            continue
            
        print("-" * 50)
        
        # Crear un nombre de archivo de salida único
        nombre_base = pathlib.Path(archivo).stem
        nombre_archivo_salida = f"{nombre_base}_procesado.pdf"
        ruta_completa_salida = os.path.join(directorio_salida, nombre_archivo_salida)
        
        procesar_y_generar_pdf(archivo, plantilla_path, ruta_completa_salida)

    print("-" * 50)
    print("🎉 Proceso completado. Revisa la carpeta 'boletos_generados'.")

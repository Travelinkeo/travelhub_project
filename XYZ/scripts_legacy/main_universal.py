# main.py UNIVERSAL - Reemplaza tu main.py actual

import os
import email
import imaplib
import re
import base64
import json
import io
from datetime import datetime
from email.header import decode_header

# Librerías de Google (mantener las tuyas)
from google.oauth2.credentials import Credentials
from google.cloud import secretmanager
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

# Librerías para procesamiento y generación de PDF (mantener las tuyas)
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

# Librerías para PDFs adjuntos (NUEVAS)
import PyPDF2
from io import BytesIO

# --- TUS FUNCIONES EXISTENTES (mantener todas) ---
def get_secret(secret_name):
    # Tu código actual - NO CAMBIAR
    pass

def get_oauth_credentials():
    # Tu código actual - NO CAMBIAR
    pass

def upload_to_google_drive(creds, pdf_bytes, file_name):
    # Tu código actual - NO CAMBIAR
    pass

# --- NUEVAS FUNCIONES PARA PARSER UNIVERSAL ---

def extract_pdf_text(pdf_bytes):
    """
    Extrae texto de un PDF adjunto
    """
    try:
        pdf_file = BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error extrayendo texto del PDF: {e}")
        return ""

def detect_ticket_system(plain_text, sender_email="", subject=""):
    """
    Detecta el sistema GDS del boleto
    """
    text = plain_text.upper()
    sender = sender_email.lower()
    subject = subject.upper()
    
    print(f"Detectando sistema - Sender: {sender}, Subject: {subject}")
    
    # KIU - Ampliado para todos los emails de kiusys.com
    if '@kiusys.com' in sender or 'KIUSYS.COM' in text or 'PASSENGER ITINERARY RECEIPT' in text:
        return 'KIU'
    
    # SABRE
    if ('ETICKET RECEIPT' in text or 'E-TICKET RECEIPT' in text) and 'RESERVATION CODE' in text:
        return 'SABRE'
    
    # AMADEUS
    if 'ELECTRONIC TICKET RECEIPT' in text and 'BOOKING REF:' in text:
        return 'AMADEUS'
    
    # Copa SPRK
    if ('copa' in sender or 'COPA AIRLINES' in text) and ('LOCALIZADOR' in text or 'SPRK' in text):
        return 'COPA_SPRK'
    
    # Wingo
    if 'wingo' in sender or 'WINGO' in text or 'WINGO.COM' in text:
        return 'WINGO'
    
    # Turkish Airlines
    if 'turkish' in sender or 'IDENTIFICACIÓN DEL PEDIDO' in text or 'GRUPO SOPORTE GLOBAL' in text:
        return 'TK_CONNECT'
    
    # Fallback: Si no se detecta, intentar con KIU
    print("Sistema no detectado específicamente, usando KIU como fallback")
    return 'KIU'

def parse_sabre_ticket(plain_text):
    """Parser SABRE - Adaptado de TravelHub"""
    print("Parseando boleto SABRE...")
    
    def extract_sabre_field(text, patterns, default='No encontrado'):
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return default
    
    data = {
        'NUMERO_DE_BOLETO': extract_sabre_field(plain_text, [
            r'TICKET NUMBER\s*[:\s]*([0-9-]+)',
            r'TKT\s*[:\s]*([0-9-]+)'
        ]),
        'FECHA_DE_EMISION': extract_sabre_field(plain_text, [
            r'DATE OF ISSUE\s*[:\s]*(.+)',
            r'ISSUE DATE\s*[:\s]*(.+)'
        ]),
        'NOMBRE_DEL_PASAJERO': extract_sabre_field(plain_text, [
            r'NAME\s*[:\s]*(.+)',
            r'PASSENGER NAME\s*[:\s]*(.+)'
        ]),
        'SOLO_CODIGO_RESERVA': extract_sabre_field(plain_text, [
            r'RESERVATION CODE\s*[:\s]*([A-Z0-9]{6})',
            r'PNR\s*[:\s]*([A-Z0-9]{6})'
        ]),
        'NOMBRE_AEROLINEA': extract_sabre_field(plain_text, [
            r'ISSUING AIRLINE\s*[:\s]*(.+)',
            r'AIRLINE\s*[:\s]*(.+)'
        ]),
        'AGENTE_EMISOR': extract_sabre_field(plain_text, [
            r'ISSUING AGENT\s*[:\s]*(.+)',
            r'AGENT\s*[:\s]*(.+)'
        ]),
        'CODIGO_IDENTIFICACION': extract_sabre_field(plain_text, [
            r'FOID\s*[:\s]*(.+)',
            r'ID\s*[:\s]*(.+)'
        ]),
        'ItinerarioFinalLimpio': extract_sabre_itinerary(plain_text),
    }
    
    # Procesar nombre del pasajero
    nombre_completo = data['NOMBRE_DEL_PASAJERO']
    if '/' in nombre_completo:
        data['SOLO_NOMBRE_PASAJERO'] = nombre_completo.split('/')[1].strip()
    else:
        data['SOLO_NOMBRE_PASAJERO'] = nombre_completo
    
    data['CODIGO_RESERVA'] = f"C1/{data['SOLO_CODIGO_RESERVA']}" if data['SOLO_CODIGO_RESERVA'] != 'No encontrado' else 'No encontrado'
    
    return data

def extract_sabre_itinerary(text):
    """Extrae itinerario de boleto SABRE"""
    lines = text.splitlines()
    itinerary_lines = []
    capturing = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Buscar inicio del itinerario
        if not capturing and ('FROM/TO' in line.upper() or 'FLIGHT' in line.upper()):
            capturing = True
            continue
            
        # Buscar fin del itinerario
        if capturing and any(keyword in line.upper() for keyword in ['FARE CALC', 'ENDORSEMENTS', 'BAGGAGE']):
            break
            
        if capturing:
            itinerary_lines.append(line)
    
    return '\n'.join(itinerary_lines) if itinerary_lines else "No se pudo extraer itinerario"

def parse_amadeus_ticket(plain_text):
    """Parser AMADEUS - Adaptado de TravelHub"""
    print("Parseando boleto AMADEUS...")
    
    def extract_amadeus_field(text, patterns, default='No encontrado'):
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return default
    
    data = {
        'NUMERO_DE_BOLETO': extract_amadeus_field(plain_text, [
            r'TICKET NUMBER\s*[:\s]*([0-9-]+)',
            r'TKT\s*[:\s]*([0-9-]+)'
        ]),
        'FECHA_DE_EMISION': extract_amadeus_field(plain_text, [
            r'DATE OF ISSUE\s*[:\s]*(.+)',
            r'ISSUE DATE\s*[:\s]*(.+)'
        ]),
        'NOMBRE_DEL_PASAJERO': extract_amadeus_field(plain_text, [
            r'NAME\s*[:\s]*(.+)',
            r'PASSENGER\s*[:\s]*(.+)'
        ]),
        'SOLO_CODIGO_RESERVA': extract_amadeus_field(plain_text, [
            r'BOOKING REF:\s*([A-Z0-9]{6})',
            r'PNR\s*[:\s]*([A-Z0-9]{6})'
        ]),
        'NOMBRE_AEROLINEA': extract_amadeus_field(plain_text, [
            r'ISSUING AIRLINE\s*[:\s]*(.+)',
            r'AIRLINE\s*[:\s]*(.+)'
        ]),
        'AGENTE_EMISOR': extract_amadeus_field(plain_text, [
            r'ISSUING AGENT\s*[:\s]*(.+)',
            r'AGENT\s*[:\s]*(.+)'
        ]),
        'CODIGO_IDENTIFICACION': extract_amadeus_field(plain_text, [
            r'FOID\s*[:\s]*(.+)',
            r'ID\s*[:\s]*(.+)'
        ]),
        'ItinerarioFinalLimpio': extract_amadeus_itinerary(plain_text),
    }
    
    # Procesar nombre
    nombre_completo = data['NOMBRE_DEL_PASAJERO']
    if '/' in nombre_completo:
        data['SOLO_NOMBRE_PASAJERO'] = nombre_completo.split('/')[1].strip()
    else:
        data['SOLO_NOMBRE_PASAJERO'] = nombre_completo
    
    data['CODIGO_RESERVA'] = f"C1/{data['SOLO_CODIGO_RESERVA']}" if data['SOLO_CODIGO_RESERVA'] != 'No encontrado' else 'No encontrado'
    
    return data

def extract_amadeus_itinerary(text):
    """Extrae itinerario de boleto AMADEUS"""
    return extract_sabre_itinerary(text)  # Similar a SABRE

def parse_copa_ticket(plain_text):
    """Parser Copa SPRK"""
    print("Parseando boleto Copa SPRK...")
    
    def extract_copa_field(text, patterns, default='No encontrado'):
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return default
    
    data = {
        'NUMERO_DE_BOLETO': extract_copa_field(plain_text, [
            r'TICKET NUMBER\s*[:\s]*([0-9]+)',
            r'BOLETO\s*[:\s]*([0-9]+)'
        ]),
        'FECHA_DE_EMISION': extract_copa_field(plain_text, [
            r'ISSUE DATE\s*[:\s]*(.+)',
            r'FECHA EMISION\s*[:\s]*(.+)'
        ]),
        'NOMBRE_DEL_PASAJERO': extract_copa_field(plain_text, [
            r'PASSENGER NAME\s*[:\s]*(.+)',
            r'NOMBRE PASAJERO\s*[:\s]*(.+)'
        ]),
        'SOLO_CODIGO_RESERVA': extract_copa_field(plain_text, [
            r'LOCALIZADOR DE RESERVA\s*[:\s]*([A-Z0-9]{6})',
            r'PNR\s*[:\s]*([A-Z0-9]{6})'
        ]),
        'NOMBRE_AEROLINEA': 'COPA AIRLINES',
        'AGENTE_EMISOR': extract_copa_field(plain_text, [
            r'ISSUING AGENT\s*[:\s]*(.+)',
            r'AGENTE\s*[:\s]*(.+)'
        ]),
        'CODIGO_IDENTIFICACION': extract_copa_field(plain_text, [
            r'FOID\s*[:\s]*(.+)',
            r'ID\s*[:\s]*(.+)'
        ]),
        'ItinerarioFinalLimpio': extract_copa_itinerary(plain_text),
    }
    
    # Procesar nombre
    nombre_completo = data['NOMBRE_DEL_PASAJERO']
    if '/' in nombre_completo:
        data['SOLO_NOMBRE_PASAJERO'] = nombre_completo.split('/')[1].strip()
    else:
        data['SOLO_NOMBRE_PASAJERO'] = nombre_completo
    
    data['CODIGO_RESERVA'] = f"C1/{data['SOLO_CODIGO_RESERVA']}" if data['SOLO_CODIGO_RESERVA'] != 'No encontrado' else 'No encontrado'
    
    return data

def extract_copa_itinerary(text):
    """Extrae itinerario de boleto Copa"""
    return extract_sabre_itinerary(text)  # Similar estructura

def parse_wingo_ticket(plain_text):
    """Parser Wingo"""
    print("Parseando boleto Wingo...")
    
    def extract_wingo_field(text, patterns, default='No encontrado'):
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return default
    
    data = {
        'NUMERO_DE_BOLETO': 'N/A',  # Wingo no genera número de boleto
        'FECHA_DE_EMISION': datetime.now().strftime('%d/%m/%Y'),
        'NOMBRE_DEL_PASAJERO': extract_wingo_field(plain_text, [
            r'PASSENGER\s*[:\s]*(.+)',
            r'PASAJERO\s*[:\s]*(.+)'
        ]),
        'SOLO_CODIGO_RESERVA': extract_wingo_field(plain_text, [
            r'BOOKING CODE\s*[:\s]*([A-Z0-9]{6})',
            r'CODIGO RESERVA\s*[:\s]*([A-Z0-9]{6})'
        ]),
        'NOMBRE_AEROLINEA': 'WINGO',
        'AGENTE_EMISOR': 'WINGO ONLINE',
        'CODIGO_IDENTIFICACION': extract_wingo_field(plain_text, [
            r'ID\s*[:\s]*(.+)',
            r'DOCUMENTO\s*[:\s]*(.+)'
        ]),
        'ItinerarioFinalLimpio': extract_wingo_itinerary(plain_text),
    }
    
    # Procesar nombre
    nombre_completo = data['NOMBRE_DEL_PASAJERO']
    if '/' in nombre_completo:
        data['SOLO_NOMBRE_PASAJERO'] = nombre_completo.split('/')[1].strip()
    else:
        data['SOLO_NOMBRE_PASAJERO'] = nombre_completo
    
    data['CODIGO_RESERVA'] = f"C1/{data['SOLO_CODIGO_RESERVA']}" if data['SOLO_CODIGO_RESERVA'] != 'No encontrado' else 'No encontrado'
    
    return data

def extract_wingo_itinerary(text):
    """Extrae itinerario de boleto Wingo"""
    return extract_sabre_itinerary(text)  # Estructura similar

def parse_tk_ticket(plain_text):
    """Parser Turkish Airlines"""
    print("Parseando boleto Turkish Airlines...")
    
    def extract_tk_field(text, patterns, default='No encontrado'):
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return default
    
    data = {
        'NUMERO_DE_BOLETO': extract_tk_field(plain_text, [
            r'TICKET NUMBER\s*[:\s]*([0-9-]+)',
            r'BOLETO\s*[:\s]*([0-9-]+)'
        ]),
        'FECHA_DE_EMISION': extract_tk_field(plain_text, [
            r'ISSUE DATE\s*[:\s]*(.+)',
            r'FECHA\s*[:\s]*(.+)'
        ]),
        'NOMBRE_DEL_PASAJERO': extract_tk_field(plain_text, [
            r'PASSENGER NAME\s*[:\s]*(.+)',
            r'NOMBRE\s*[:\s]*(.+)'
        ]),
        'SOLO_CODIGO_RESERVA': extract_tk_field(plain_text, [
            r'PNR\s*[:\s]*([A-Z0-9]{6})',
            r'RESERVA\s*[:\s]*([A-Z0-9]{6})'
        ]),
        'NOMBRE_AEROLINEA': 'TURKISH AIRLINES',
        'AGENTE_EMISOR': extract_tk_field(plain_text, [
            r'ISSUING AGENT\s*[:\s]*(.+)',
            r'AGENTE\s*[:\s]*(.+)'
        ]),
        'CODIGO_IDENTIFICACION': extract_tk_field(plain_text, [
            r'ID\s*[:\s]*(.+)',
            r'DOCUMENTO\s*[:\s]*(.+)'
        ]),
        'ItinerarioFinalLimpio': extract_tk_itinerary(plain_text),
    }
    
    # Procesar nombre
    nombre_completo = data['NOMBRE_DEL_PASAJERO']
    if '/' in nombre_completo:
        data['SOLO_NOMBRE_PASAJERO'] = nombre_completo.split('/')[1].strip()
    else:
        data['SOLO_NOMBRE_PASAJERO'] = nombre_completo
    
    data['CODIGO_RESERVA'] = f"C1/{data['SOLO_CODIGO_RESERVA']}" if data['SOLO_CODIGO_RESERVA'] != 'No encontrado' else 'No encontrado'
    
    return data

def extract_tk_itinerary(text):
    """Extrae itinerario de Turkish Airlines"""
    return extract_sabre_itinerary(text)  # Estructura similar

def parse_universal_ticket(plain_text, html_text="", sender_email="", subject=""):
    """
    Parser universal que detecta y parsea cualquier tipo de boleto
    """
    system = detect_ticket_system(plain_text, sender_email, subject)
    print(f"Sistema detectado: {system}")
    
    if system == 'KIU':
        return extract_data_from_text(plain_text, html_text)  # Tu función actual
    elif system == 'SABRE':
        return parse_sabre_ticket(plain_text)
    elif system == 'AMADEUS':
        return parse_amadeus_ticket(plain_text)
    elif system == 'COPA_SPRK':
        return parse_copa_ticket(plain_text)
    elif system == 'WINGO':
        return parse_wingo_ticket(plain_text)
    elif system == 'TK_CONNECT':
        return parse_tk_ticket(plain_text)
    else:
        print(f"Sistema no reconocido, intentando con KIU...")
        return extract_data_from_text(plain_text, html_text)

def enviar_a_travelhub(ticket_data, pdf_bytes, pdf_filename):
    """
    Envía datos parseados a TravelHub
    """
    try:
        import requests
        
        TRAVELHUB_URL = os.environ.get("TRAVELHUB_URL", "https://tu-travelhub.onrender.com")
        
        travelhub_data = {
            'source': 'universal_automation',
            'numero_boleto': ticket_data.get('NUMERO_DE_BOLETO'),
            'localizador_pnr': ticket_data.get('SOLO_CODIGO_RESERVA'),
            'nombre_pasajero_completo': ticket_data.get('NOMBRE_DEL_PASAJERO'),
            'aerolinea_emisora': ticket_data.get('NOMBRE_AEROLINEA'),
            'fecha_emision_boleto': ticket_data.get('FECHA_DE_EMISION'),
            'total_boleto': 0.0,
            'datos_parseados': {
                'SOURCE_SYSTEM': detect_ticket_system(str(ticket_data)),
                'normalized': {
                    'reservation_code': ticket_data.get('SOLO_CODIGO_RESERVA'),
                    'ticket_number': ticket_data.get('NUMERO_DE_BOLETO'),
                    'passenger_name': ticket_data.get('NOMBRE_DEL_PASAJERO'),
                    'passenger_document': ticket_data.get('CODIGO_IDENTIFICACION'),
                    'airline_name': ticket_data.get('NOMBRE_AEROLINEA'),
                    'itinerary': ticket_data.get('ItinerarioFinalLimpio'),
                }
            },
            'estado_parseo': 'COM'
        }
        
        response = requests.post(
            f"{TRAVELHUB_URL}/api/boletos-importados/webhook/",
            json=travelhub_data,
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ Datos enviados a TravelHub exitosamente")
        else:
            print(f"⚠️ Error enviando a TravelHub: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ Error conectando con TravelHub: {e}")

# --- FUNCIÓN PRINCIPAL MODIFICADA ---
def process_tickets_main_logic():
    """
    Función principal UNIVERSAL - Reemplaza tu función actual
    """
    print("Iniciando el proceso de revisión de boletos UNIVERSALES...")
    try:
        GMAIL_USER, GMAIL_APP_PASSWORD = get_secret("gmail-user"), get_secret("gmail-app-password")
        gdrive_creds = get_oauth_credentials()
        
        print(f"Conectando a Gmail como {GMAIL_USER}...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("inbox")
        print("Conexión a Gmail exitosa.")
        
        # BÚSQUEDA AMPLIADA - TODOS LOS SISTEMAS
        search_criteria = '''(UNSEEN (OR (OR (OR (OR (OR (OR
            (FROM "@kiusys.com")
            (SUBJECT "ETICKET RECEIPT"))
            (SUBJECT "E-TICKET RECEIPT"))
            (SUBJECT "ELECTRONIC TICKET RECEIPT"))
            (FROM "@copaair.com"))
            (FROM "@wingo.com"))
            (FROM "@turkishairlines.com")))'''
        
        status, messages = mail.search(None, search_criteria)
        
        if status != "OK" or not messages[0]:
            print("No se encontraron nuevos correos para procesar.")
            mail.logout()
            return

        email_ids = messages[0].split()
        print(f"Se encontraron {len(email_ids)} correo(s) nuevo(s).")
        
        for email_id in email_ids:
            try:
                print(f"\n--- Procesando email ID: {email_id.decode()} ---")
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1], policy=email.policy.default)
                
                # Obtener información del email
                sender_email = msg.get('From', '')
                subject = msg.get('Subject', '')
                print(f"De: {sender_email}, Asunto: {subject}")
                
                html_body = ""
                plain_text = ""
                pdf_attachments = []
                
                # PROCESAR MULTIPART (INCLUYENDO ADJUNTOS)
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get('Content-Disposition'))
                        charset = part.get_content_charset() or 'utf-8'
                        
                        # ADJUNTOS PDF
                        if 'attachment' in content_disposition and content_type == 'application/pdf':
                            filename = part.get_filename()
                            if filename:
                                pdf_data = part.get_payload(decode=True)
                                pdf_text = extract_pdf_text(pdf_data)
                                if pdf_text.strip():
                                    pdf_attachments.append({
                                        'filename': filename,
                                        'text': pdf_text
                                    })
                                    print(f"PDF adjunto procesado: {filename}")
                        
                        # CONTENIDO DEL EMAIL
                        elif 'attachment' not in content_disposition:
                            if "text/html" in content_type:
                                html_body = part.get_payload(decode=True).decode(charset, errors='ignore')
                            elif "text/plain" in content_type:
                                plain_text = part.get_payload(decode=True).decode(charset, errors='ignore')
                else:
                    # EMAIL SIMPLE (NO MULTIPART)
                    charset = msg.get_content_charset() or 'utf-8'
                    payload = msg.get_payload(decode=True)
                    if payload:
                        if "text/html" in msg.get_content_type():
                            html_body = payload.decode(charset, errors='ignore')
                        else:
                            plain_text = payload.decode(charset, errors='ignore')

                # PROCESAR CONTENIDO DEL EMAIL (KIU principalmente)
                if not plain_text and html_body:
                    plain_text = BeautifulSoup(html_body, 'html.parser').get_text(separator='\n')
                
                # PROCESAR BOLETOS
                tickets_processed = 0
                
                # 1. PROCESAR CONTENIDO DEL EMAIL (KIU)
                if plain_text.strip():
                    try:
                        ticket_data = parse_universal_ticket(plain_text, html_body, sender_email, subject)
                        
                        if ticket_data.get('SOLO_CODIGO_RESERVA') != 'No encontrado':
                            pdf_bytes, pdf_filename = generate_ticket(ticket_data)
                            upload_to_google_drive(gdrive_creds, pdf_bytes, pdf_filename)
                            enviar_a_travelhub(ticket_data, pdf_bytes, pdf_filename)
                            tickets_processed += 1
                            print(f"✅ Boleto del email procesado: {ticket_data.get('NUMERO_DE_BOLETO')}")
                    except Exception as e:
                        print(f"Error procesando contenido del email: {e}")
                
                # 2. PROCESAR PDFs ADJUNTOS (SABRE, AMADEUS, etc.)
                for pdf_attachment in pdf_attachments:
                    try:
                        ticket_data = parse_universal_ticket(pdf_attachment['text'], "", sender_email, subject)
                        
                        if ticket_data.get('SOLO_CODIGO_RESERVA') != 'No encontrado':
                            pdf_bytes, pdf_filename = generate_ticket(ticket_data)
                            upload_to_google_drive(gdrive_creds, pdf_bytes, pdf_filename)
                            enviar_a_travelhub(ticket_data, pdf_bytes, pdf_filename)
                            tickets_processed += 1
                            print(f"✅ Boleto del PDF procesado: {ticket_data.get('NUMERO_DE_BOLETO')}")
                    except Exception as e:
                        print(f"Error procesando PDF {pdf_attachment['filename']}: {e}")
                
                if tickets_processed > 0:
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    print(f"✅ Email procesado - {tickets_processed} boleto(s) generado(s)")
                else:
                    print("⚠️ No se pudieron extraer datos válidos del email")

            except Exception as e:
                import traceback
                print(f"Error procesando el email ID {email_id.decode()}: {e}")
                traceback.print_exc()
                continue
        
        mail.logout()
        print("Proceso completado.")
    except Exception as e:
        import traceback
        print(f"Ocurrió un error crítico general: {e}")
        traceback.print_exc()

# --- TUS FUNCIONES EXISTENTES (mantener todas sin cambios) ---
def _extract_field(texto: str, patterns: list, default='No encontrado') -> str:
    # Tu código actual - NO CAMBIAR
    pass

def _extract_block(texto: str, start_patterns: list, end_patterns: list, default='No encontrado') -> str:
    # Tu código actual - NO CAMBIAR
    pass

# ... TODAS TUS OTRAS FUNCIONES EXISTENTES ...

def generate_ticket(data):
    # Tu código actual - NO CAMBIAR
    pass

# --- PUNTO DE ENTRADA PARA CLOUD FUNCTIONS (PUB/SUB) ---
def pubsub_trigger(event, context):
    print("Función activada por Pub/Sub.")
    process_tickets_main_logic()
    print("Ejecución de la función finalizada.")
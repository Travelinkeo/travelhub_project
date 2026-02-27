"""
Parser Universal para Google Cloud Functions
Integra todos los parsers de TravelHub en tu proyecto KIU existente
"""

# AGREGAR A TU main.py EXISTENTE:

def detect_ticket_system(plain_text, html_text=""):
    """
    Detecta el sistema GDS del boleto
    """
    text = plain_text.upper()
    
    # KIU (tu sistema actual)
    if 'KIUSYS.COM' in text or 'PASSENGER ITINERARY RECEIPT' in text:
        return 'KIU'
    
    # SABRE
    if 'ETICKET RECEIPT' in text and 'RESERVATION CODE' in text:
        return 'SABRE'
    
    # AMADEUS
    if 'ELECTRONIC TICKET RECEIPT' in text and 'BOOKING REF:' in text:
        return 'AMADEUS'
    
    # Copa SPRK
    if 'COPA AIRLINES' in text and ('LOCALIZADOR DE RESERVA' in text or 'SPRK' in text):
        return 'COPA_SPRK'
    
    # Wingo
    if 'WINGO' in text or 'WINGO.COM' in text:
        return 'WINGO'
    
    # TK Connect
    if 'IDENTIFICACIÓN DEL PEDIDO' in text or 'GRUPO SOPORTE GLOBAL' in text:
        return 'TK_CONNECT'
    
    return 'UNKNOWN'

def parse_sabre_ticket(plain_text):
    """Parser SABRE simplificado"""
    data = {
        'NUMERO_DE_BOLETO': _extract_field(plain_text, [r'TICKET NUMBER\s*[:\s]*([0-9-]+)']),
        'FECHA_DE_EMISION': _extract_field(plain_text, [r'DATE OF ISSUE\s*[:\s]*(.+)']),
        'NOMBRE_DEL_PASAJERO': _extract_field(plain_text, [r'NAME\s*[:\s]*(.+)']),
        'SOLO_CODIGO_RESERVA': _extract_field(plain_text, [r'RESERVATION CODE\s*[:\s]*([A-Z0-9]{6})']),
        'NOMBRE_AEROLINEA': _extract_field(plain_text, [r'ISSUING AIRLINE\s*[:\s]*(.+)']),
        'AGENTE_EMISOR': _extract_field(plain_text, [r'ISSUING AGENT\s*[:\s]*(.+)']),
        'ItinerarioFinalLimpio': extraer_itinerario_sabre(plain_text),
    }
    return data

def parse_amadeus_ticket(plain_text):
    """Parser AMADEUS simplificado"""
    data = {
        'NUMERO_DE_BOLETO': _extract_field(plain_text, [r'TICKET NUMBER\s*[:\s]*([0-9-]+)']),
        'FECHA_DE_EMISION': _extract_field(plain_text, [r'DATE OF ISSUE\s*[:\s]*(.+)']),
        'NOMBRE_DEL_PASAJERO': _extract_field(plain_text, [r'NAME\s*[:\s]*(.+)']),
        'SOLO_CODIGO_RESERVA': _extract_field(plain_text, [r'BOOKING REF:\s*([A-Z0-9]{6})']),
        'NOMBRE_AEROLINEA': _extract_field(plain_text, [r'ISSUING AIRLINE\s*[:\s]*(.+)']),
        'AGENTE_EMISOR': _extract_field(plain_text, [r'ISSUING AGENT\s*[:\s]*(.+)']),
        'ItinerarioFinalLimpio': extraer_itinerario_amadeus(plain_text),
    }
    return data

def parse_copa_ticket(plain_text):
    """Parser Copa SPRK simplificado"""
    data = {
        'NUMERO_DE_BOLETO': _extract_field(plain_text, [r'TICKET NUMBER\s*[:\s]*([0-9]+)']),
        'FECHA_DE_EMISION': _extract_field(plain_text, [r'ISSUE DATE\s*[:\s]*(.+)']),
        'NOMBRE_DEL_PASAJERO': _extract_field(plain_text, [r'PASSENGER NAME\s*[:\s]*(.+)']),
        'SOLO_CODIGO_RESERVA': _extract_field(plain_text, [r'LOCALIZADOR DE RESERVA\s*[:\s]*([A-Z0-9]{6})']),
        'NOMBRE_AEROLINEA': 'COPA AIRLINES',
        'AGENTE_EMISOR': _extract_field(plain_text, [r'ISSUING AGENT\s*[:\s]*(.+)']),
        'ItinerarioFinalLimpio': extraer_itinerario_copa(plain_text),
    }
    return data

def parse_wingo_ticket(plain_text):
    """Parser Wingo simplificado"""
    data = {
        'NUMERO_DE_BOLETO': 'N/A',  # Wingo no genera número de boleto
        'FECHA_DE_EMISION': datetime.now().strftime('%d/%m/%Y'),
        'NOMBRE_DEL_PASAJERO': _extract_field(plain_text, [r'PASSENGER\s*[:\s]*(.+)']),
        'SOLO_CODIGO_RESERVA': _extract_field(plain_text, [r'BOOKING CODE\s*[:\s]*([A-Z0-9]{6})']),
        'NOMBRE_AEROLINEA': 'WINGO',
        'AGENTE_EMISOR': 'WINGO ONLINE',
        'ItinerarioFinalLimpio': extraer_itinerario_wingo(plain_text),
    }
    return data

def parse_tk_ticket(plain_text):
    """Parser TK Connect simplificado"""
    data = {
        'NUMERO_DE_BOLETO': _extract_field(plain_text, [r'TICKET NUMBER\s*[:\s]*([0-9-]+)']),
        'FECHA_DE_EMISION': _extract_field(plain_text, [r'ISSUE DATE\s*[:\s]*(.+)']),
        'NOMBRE_DEL_PASAJERO': _extract_field(plain_text, [r'PASSENGER NAME\s*[:\s]*(.+)']),
        'SOLO_CODIGO_RESERVA': _extract_field(plain_text, [r'PNR\s*[:\s]*([A-Z0-9]{6})']),
        'NOMBRE_AEROLINEA': 'TURKISH AIRLINES',
        'AGENTE_EMISOR': _extract_field(plain_text, [r'ISSUING AGENT\s*[:\s]*(.+)']),
        'ItinerarioFinalLimpio': extraer_itinerario_tk(plain_text),
    }
    return data

def parse_universal_ticket(plain_text, html_text=""):
    """
    Parser universal que detecta y parsea cualquier tipo de boleto
    """
    system = detect_ticket_system(plain_text, html_text)
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

# MODIFICAR TU FUNCIÓN PRINCIPAL:
def process_tickets_main_logic():
    """
    Función principal modificada para manejar múltiples sistemas
    """
    print("Iniciando el proceso de revisión de boletos universales...")
    try:
        GMAIL_USER, GMAIL_APP_PASSWORD = get_secret("gmail-user"), get_secret("gmail-app-password")
        gdrive_creds = get_oauth_credentials()
        
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("inbox")
        
        # BÚSQUEDA AMPLIADA - No solo KIU
        search_criteria = '(UNSEEN (OR (OR (OR (OR (OR ' \
                         '(FROM "noreply@kiusys.com" SUBJECT "E-TICKET ITINERARY RECEIPT") ' \
                         '(SUBJECT "ETICKET RECEIPT")) ' \
                         '(SUBJECT "ELECTRONIC TICKET RECEIPT")) ' \
                         '(FROM "noreply@copaair.com")) ' \
                         '(FROM "reservas@wingo.com")) ' \
                         '(FROM "noreply@turkishairlines.com")))'
        
        status, messages = mail.search(None, search_criteria)
        
        if status != "OK" or not messages[0]:
            print("No se encontraron nuevos correos para procesar.")
            mail.logout()
            return

        email_ids = messages[0].split()
        print(f"Se encontraron {len(email_ids)} correo(s) nuevo(s).")
        
        for email_id in email_ids:
            try:
                # ... tu código de extracción de email existente ...
                
                # USAR PARSER UNIVERSAL
                ticket_data = parse_universal_ticket(plain_text, html_body)
                
                # Generar PDF (tu función actual funciona para todos)
                pdf_bytes, pdf_filename = generate_ticket(ticket_data)
                
                # Subir a Drive (mantener)
                upload_to_google_drive(gdrive_creds, pdf_bytes, pdf_filename)
                
                # Enviar a TravelHub (nuevo)
                enviar_a_travelhub(ticket_data, pdf_bytes, pdf_filename)
                
                mail.store(email_id, '+FLAGS', '\\Seen')
                print(f"Boleto {ticket_data.get('NUMERO_DE_BOLETO')} procesado exitosamente")

            except Exception as e:
                print(f"Error procesando email: {e}")
                continue
        
        mail.logout()
        print("Proceso completado.")
        
    except Exception as e:
        print(f"Error crítico: {e}")

# Funciones auxiliares de itinerario (simplificadas)
def extraer_itinerario_sabre(text):
    return _extract_block(text, ['FROM/TO'], ['ENDORSEMENTS', 'FARE CALC'])

def extraer_itinerario_amadeus(text):
    return _extract_block(text, ['FROM/TO'], ['FARE CALCULATION'])

def extraer_itinerario_copa(text):
    return _extract_block(text, ['FLIGHT DETAILS'], ['FARE BASIS'])

def extraer_itinerario_wingo(text):
    return _extract_block(text, ['FLIGHT'], ['TOTAL'])

def extraer_itinerario_tk(text):
    return _extract_block(text, ['FLIGHT DETAILS'], ['FARE'])
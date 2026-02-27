"""
Integración KIU → TravelHub
Modificación mínima a tu main.py existente
"""

# AGREGAR AL FINAL DE TU main.py EXISTENTE:

def enviar_a_travelhub(ticket_data, pdf_bytes, pdf_filename):
    """
    Envía datos parseados a TravelHub después de procesar
    """
    try:
        import requests
        
        # URL de tu TravelHub (cuando esté desplegado)
        TRAVELHUB_URL = os.environ.get("TRAVELHUB_URL", "https://tu-travelhub.onrender.com")
        
        # Preparar datos para TravelHub
        travelhub_data = {
            'source': 'kiu_automation',
            'numero_boleto': ticket_data.get('NUMERO_DE_BOLETO'),
            'localizador_pnr': ticket_data.get('SOLO_CODIGO_RESERVA'),
            'nombre_pasajero_completo': ticket_data.get('NOMBRE_DEL_PASAJERO'),
            'aerolinea_emisora': ticket_data.get('NOMBRE_AEROLINEA'),
            'fecha_emision_boleto': ticket_data.get('FECHA_DE_EMISION'),
            'total_boleto': 0.0,  # KIU no siempre tiene precio
            'datos_parseados': {
                'SOURCE_SYSTEM': 'KIU',
                'normalized': {
                    'reservation_code': ticket_data.get('SOLO_CODIGO_RESERVA'),
                    'ticket_number': ticket_data.get('NUMERO_DE_BOLETO'),
                    'passenger_name': ticket_data.get('NOMBRE_DEL_PASAJERO'),
                    'passenger_document': ticket_data.get('CODIGO_IDENTIFICACION'),
                    'airline_name': ticket_data.get('NOMBRE_AEROLINEA'),
                    'itinerary': ticket_data.get('ItinerarioFinalLimpio'),
                }
            },
            'estado_parseo': 'COM'  # Completado
        }
        
        # Enviar a TravelHub
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
        # No fallar si TravelHub no está disponible


# MODIFICAR LA FUNCIÓN process_tickets_main_logic():
# Agregar esta línea después de upload_to_google_drive():

def process_tickets_main_logic():
    # ... tu código existente ...
    
    for email_id in email_ids:
        try:
            # ... tu código de parseo existente ...
            
            ticket_data = extract_data_from_text(plain_text, html_body)
            pdf_bytes, pdf_filename = generate_ticket(ticket_data)
            
            # Tu funcionalidad actual (mantener)
            upload_to_google_drive(gdrive_creds, pdf_bytes, pdf_filename)
            
            # NUEVA LÍNEA: Enviar a TravelHub
            enviar_a_travelhub(ticket_data, pdf_bytes, pdf_filename)
            
            mail.store(email_id, '+FLAGS', '\\Seen')
            
        except Exception as e:
            # ... tu manejo de errores existente ...
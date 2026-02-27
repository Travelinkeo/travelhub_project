
import sys
import os
import json
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up Django environment
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

# Configure logging to print to stderr
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

from core.parsers.sabre_parser import SabreParser
from core.ticket_parser import generate_ticket

# The data provided by the user (simulated)
user_json = """
{"pnr": "EJVZRZ", "total": null, "vuelos": [{"cabina": "TURISTA", "origen": {"pais": "COLOMBIA", "ciudad": "BOGOTA"}, "destino": {"pais": null, "ciudad": "PARIS DE GAULLE"}, "equipaje": "1PC", "aerolinea": "Air France", "hora_salida": "23:55", "fecha_salida": "07 abr 25", "hora_llegada": "17:10", "numero_vuelo": "AF435", "fecha_llegada": "08 abr 25", "codigo_reservacion_local": "No encontrado"}, {"cabina": "TURISTA", "origen": {"pais": "SHANGHAI", "ciudad": "PARIS DE GAULLE"}, "destino": {"pais": null, "ciudad": "PUDONG"}, "equipaje": "1PC", "aerolinea": "Air France", "hora_salida": "23:30", "fecha_salida": "08 abr 25", "hora_llegada": "18:15", "numero_vuelo": "AF116", "fecha_llegada": "09 abr 25", "codigo_reservacion_local": "No encontrado"}, {"cabina": "PREMIUM", "origen": {"pais": "PARIS", "ciudad": "SHANGHAI PUDONG"}, "destino": {"pais": null, "ciudad": "DE GAULLE"}, "equipaje": "1PC", "aerolinea": "Air France", "hora_salida": "21:30", "fecha_salida": "20 abr 25", "hora_llegada": "05:50", "numero_vuelo": "AF111", "fecha_llegada": "21 abr 25", "codigo_reservacion_local": "No encontrado"}, {"cabina": "PREMIUM", "origen": {"pais": "BOGOTA", "ciudad": "PARIS DE GAULLE"}, "equipaje": "1PC", "aerolinea": "Air France", "hora_salida": "19:20", "fecha_salida": "21 abr 25", "hora_llegada": "15:25", "numero_vuelo": "AF436", "fecha_llegada": null, "codigo_reservacion_local": "No encontrado"}], "agencia": {"iata": "10617390", "agent": "GRUPO SOPORTE GLOBAL INC/ASP"}, "flights": [{"cabina": "TURISTA", "origen": {"pais": "COLOMBIA", "ciudad": "BOGOTA"}, "destino": {"pais": null, "ciudad": "PARIS DE GAULLE"}, "equipaje": "1PC", "aerolinea": "Air France", "hora_salida": "23:55", "fecha_salida": "07 abr 25", "hora_llegada": "17:10", "numero_vuelo": "AF435", "fecha_llegada": "08 abr 25", "codigo_reservacion_local": "No encontrado"}, {"cabina": "TURISTA", "origen": {"pais": "SHANGHAI", "ciudad": "PARIS DE GAULLE"}, "destino": {"pais": null, "ciudad": "PUDONG"}, "equipaje": "1PC", "aerolinea": "Air France", "hora_salida": "23:30", "fecha_salida": "08 abr 25", "hora_llegada": "18:15", "numero_vuelo": "AF116", "fecha_llegada": "09 abr 25", "codigo_reservacion_local": "No encontrado"}, {"cabina": "PREMIUM", "origen": {"pais": "PARIS", "ciudad": "SHANGHAI PUDONG"}, "destino": {"pais": null, "ciudad": "DE GAULLE"}, "equipaje": "1PC", "aerolinea": "Air France", "hora_salida": "21:30", "fecha_salida": "20 abr 25", "hora_llegada": "05:50", "numero_vuelo": "AF111", "fecha_llegada": "21 abr 25", "codigo_reservacion_local": "No encontrado"}, {"cabina": "PREMIUM", "origen": {"pais": "BOGOTA", "ciudad": "PARIS DE GAULLE"}, "equipaje": "1PC", "aerolinea": "Air France", "hora_salida": "19:20", "fecha_salida": "21 abr 25", "hora_llegada": "15:25", "numero_vuelo": "AF436", "fecha_llegada": null, "codigo_reservacion_local": "No encontrado"}], "reserva": {"agente_emisor": {"nombre": "GRUPO SOPORTE GLOBAL INC/ASP", "numero_iata": "10617390"}, "numero_boleto": "0577247360995", "aerolinea_emisora": "Air France", "fecha_emision_iso": "2025-03-28", "codigo_reservacion": "EJVZRZ"}, "tarifas": {"fare_amount": null, "total_amount": null, "fare_currency": null, "total_currency": null}, "pasajero": {"nombre_completo": "CASTANO VALENCIA/ALEXANDER", "documento_identidad": "AT278914"}, "itinerario": {"vuelos": [{"cabina": "TURISTA", "origen": {"pais": "COLOMBIA", "ciudad": "BOGOTA"}, "destino": {"pais": null, "ciudad": "PARIS DE GAULLE"}, "equipaje": "1PC", "aerolinea": "Air France", "hora_salida": "23:55", "fecha_salida": "07 abr 25", "hora_llegada": "17:10", "numero_vuelo": "AF435", "fecha_llegada": "08 abr 25", "codigo_reservacion_local": "No encontrado"}, {"cabina": "TURISTA", "origen": {"pais": "SHANGHAI", "ciudad": "PARIS DE GAULLE"}, "destino": {"pais": null, "ciudad": "PUDONG"}, "equipaje": "1PC", "aerolinea": "Air France", "hora_salida": "23:30", "fecha_salida": "08 abr 25", "hora_llegada": "18:15", "numero_vuelo": "AF116", "fecha_llegada": "09 abr 25", "codigo_reservacion_local": "No encontrado"}, {"cabina": "PREMIUM", "origen": {"pais": "PARIS", "ciudad": "SHANGHAI PUDONG"}, "destino": {"pais": null, "ciudad": "DE GAULLE"}, "equipaje": "1PC", "aerolinea": "Air France", "hora_salida": "21:30", "fecha_salida": "20 abr 25", "hora_llegada": "05:50", "numero_vuelo": "AF111", "fecha_llegada": "21 abr 25", "codigo_reservacion_local": "No encontrado"}, {"cabina": "PREMIUM", "origen": {"pais": "BOGOTA", "ciudad": "PARIS DE GAULLE"}, "equipaje": "1PC", "aerolinea": "Air France", "hora_salida": "19:20", "fecha_salida": "21 abr 25", "hora_llegada": "15:25", "numero_vuelo": "AF436", "fecha_llegada": null, "codigo_reservacion_local": "No encontrado"}]}, "airline_name": "Air France", "SOURCE_SYSTEM": "SABRE", "fecha_emision": "2025-03-28", "numero_boleto": "0577247360995", "ticket_number": "0577247360995", "passenger_name": "CASTANO VALENCIA/ALEXANDER"}
"""

data = json.loads(user_json)

# Force debug level for ticket parser manually
logging.getLogger('core.ticket_parser').setLevel(logging.DEBUG)

print("Generating PDF...")
try:
    pdf_bytes, filename = generate_ticket(data)
    if pdf_bytes:
        print(f"Success! PDF generated: {filename} ({len(pdf_bytes)} bytes)")
    else:
        print(f"Failed! generate_ticket returned empty bytes. Filename: {filename}")
except Exception as e:
    print(f"ERROR_MAIN_BLOCK: {e}")
    import traceback
    traceback.print_exc()

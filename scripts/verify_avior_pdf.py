import sys
import os
import logging
from pathlib import Path

# Setup Django environment
sys.path.append(str(Path.cwd()))
# Force UTF-8 for Windows console output
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
import django
django.setup()

from core.ticket_parser import generate_ticket

# Data from user log
data = {
    "vuelos": [{"clase": "ECONOMY", "fecha": "02FEB26", "origen": "CARACAS", "destino": "", "equipaje": "1PC", "aerolinea": "AVIOR AIRLINES C.A", "hora_salida": "17:00", "fecha_salida": "2026-02-02", "hora_llegada": "18:00", "numero_vuelo": "9V 062"}],
    "IMPUESTOS": "7146.79",
    "TOTAL_MONEDA": "VES",
    "AGENTE_EMISOR": "BLA009VWW",
    "FECHA_EMISION": "29ENE26",
    "SOURCE_SYSTEM": "AVIOR_WEB_PDF",
    "TOTAL_IMPORTE": "28975.42",
    "CODIGO_RESERVA": "TQRULO",
    "TARIFA_IMPORTE": "21828.63",
    "NOMBRE_AEROLINEA": "AVIOR AIRLINES C.A",
    "NUMERO_DE_BOLETO": "7420200050864",
    "DIRECCION_AEROLINEA": "AV JORGE RODRIGUEZ CC MT NIVEL PB LC 35 ANZOATEGUI",
    "NOMBRE_DEL_PASAJERO": "SARIBEL LEZAMA DE ZULUAGA",
    "SOLO_CODIGO_RESERVA": "TQRULO",
    "SOLO_NOMBRE_PASAJERO": "SARIBEL",
    "CODIGO_IDENTIFICACION": "PENDIENTE",
    "ruta": "CARACAS - ..." # Fake route for testing
}

# Configure logging to stdout
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('core.ticket_parser')
logger.setLevel(logging.DEBUG)

print("--- Generating Ticket ---")
try:
    pdf_bytes, filename = generate_ticket(data)
    print(f"Result: {len(pdf_bytes)} bytes, Filename: {filename}")
    
    if len(pdf_bytes) > 0:
        with open("test_avior.pdf", "wb") as f:
            f.write(pdf_bytes)
        print("PDF saved to test_avior.pdf")
    else:
        print("❌ PDF bytes are empty!")
except Exception as e:
    print(f"❌ Exception: {e}")

import email
from email import policy
import os
import sys
import django
import json
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv()
os.environ["GEMINI_API_KEY"] = "AIzaSyBsQWW6Yz_Hd3vAYKK5sV7W_vZz4jffkVM"
os.environ["GOOGLE_API_KEY"] = "AIzaSyBsQWW6Yz_Hd3vAYKK5sV7W_vZz4jffkVM"

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(r'c:\Users\ARMANDO\travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.ticket_parser import extract_data_from_text

def test_ai_parser(file_path):
    print(f"\n{'='*60}")
    print(f"🔬 TESTING AI PARSER: {os.path.basename(file_path)}")
    print(f"{'='*60}")
    
    with open(file_path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    plain_part = msg.get_body(preferencelist=('plain',))
    html_part = msg.get_body(preferencelist=('html',))

    plain_text = plain_part.get_content() if plain_part else ""
    html_text = html_part.get_content() if html_part else ""

    # Ejecutar el nuevo motor
    data = extract_data_from_text(plain_text, html_text)
    
    if "error" in data:
        print(f"❌ ERROR: {data['error']}")
        return

    print(f"✅ SOURCE SYSTEM: {data.get('SOURCE_SYSTEM')}")
    print(f"👤 PASAJERO: {data.get('NOMBRE_DEL_PASAJERO')}")
    print(f"👋 SALUDO: {data.get('SOLO_NOMBRE_PASAJERO')}")
    print(f"🎫 BOLETO: {data.get('NUMERO_DE_BOLETO')}")
    print(f"🔑 PNR: {data.get('CODIGO_RESERVA')}")
    print(f"🏢 AGENTE: {data.get('AGENTE_EMISOR')}")
    print(f"✈️ VUELOS: {len(data.get('vuelos', []))} segmentos")
    
    for i, v in enumerate(data.get('vuelos', []), 1):
        print(f"   [{i}] {v.get('aerolinea')} {v.get('numero_vuelo')}: {v.get('origen')} -> {v.get('destino')} ({v.get('fecha_salida')})")
    
    print(f"💰 TOTAL: {data.get('TOTAL')}")
    print(f"{'-'*60}")

# Archivos de prueba
kiu_file = r'C:\Users\ARMANDO\travelhub_project\media\boletos_importados\2026\02\Recibo_de_pasaje_electrónico_09_marz_i9uVo57.pdf'
sabre_file = r'C:\Users\ARMANDO\travelhub_project\media\boletos_importados\2026\02\ZULUAGA_RIVILLAS_DIEGO_FERNANDO_MR_04MAY2025_CCS_IST.eml'

if __name__ == "__main__":
    if os.path.exists(kiu_file):
        test_ai_parser(kiu_file)
    else:
        print(f"Falta archivo KIU: {kiu_file}")
        
    if os.path.exists(sabre_file):
        test_ai_parser(sabre_file)
    else:
        print(f"Falta archivo Sabre: {sabre_file}")

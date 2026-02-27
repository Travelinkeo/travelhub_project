import email
from email import policy
import os
import sys
import django
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
os.environ["GEMINI_API_KEY"] = "AIzaSyBsQWW6Yz_Hd3vAYKK5sV7W_vZz4jffkVM"

# Add project root to path
sys.path.append(r'c:\Users\ARMANDO\travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

import core.parsers.ai_universal_parser as ai_mod
import core.ticket_parser as tp_mod
print(f"🕵️ [MODULE CHECK] ai_universal_parser: {ai_mod.__file__}")
print(f"🕵️ [MODULE CHECK] ticket_parser: {tp_mod.__file__}")

from core.ticket_parser import extract_data_from_text

def test_ai_parser(file_path):
    print(f"\n🔬 TESTING: {os.path.basename(file_path)}")
    try:
        with open(file_path, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=policy.default)
        plain_text = msg.get_body(preferencelist=('plain',)).get_content() if msg.get_body() else ""
        
        data = extract_data_from_text(plain_text, "")
        print(f"✅ SOURCE: {data.get('SOURCE_SYSTEM')}")
        print(f"👤 PASAJERO: {data.get('NOMBRE_DEL_PASAJERO')}")
    except Exception as e:
        print(f"❌ ERROR EN TEST: {e}")

sabre_file = r'C:\Users\ARMANDO\travelhub_project\media\boletos_importados\2026\02\ZULUAGA_RIVILLAS_DIEGO_FERNANDO_MR_04MAY2025_CCS_IST.eml'
if __name__ == "__main__":
    if os.path.exists(sabre_file):
        test_ai_parser(sabre_file)

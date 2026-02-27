import os
import sys
import logging

# Configurar logging ANTES de que Django lo haga
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("--- INICIO AUDITORIA DE LOGGING ---")

import email
from email import policy
import django
from dotenv import load_dotenv

load_dotenv()
os.environ["GEMINI_API_KEY"] = "AIzaSyBsQWW6Yz_Hd3vAYKK5sV7W_vZz4jffkVM"

sys.path.append(r'c:\Users\ARMANDO\travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

# Mostrar donde estan los archivos
import core.parsers.ai_universal_parser as ai_mod
print(f"FILE_AI: {ai_mod.__file__}")

from core.ticket_parser import extract_data_from_text

# Forzar nivel INFO en el modulo IA
logging.getLogger('core.parsers.ai_universal_parser').setLevel(logging.INFO)

def test_ai_parser(file_path):
    print(f"\n🔬 TRABAJANDO CON: {file_path}")
    try:
        with open(file_path, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=policy.default)
        
        body = msg.get_body(preferencelist=('plain',))
        plain_text = body.get_content() if body else ""
        
        data = extract_data_from_text(plain_text, "")
        print(f"RESULT_SOURCE: {data.get('SOURCE_SYSTEM')}")
        print(f"RESULT_PASAJERO: {data.get('NOMBRE_DEL_PASAJERO')}")
    except Exception as e:
        print(f"RESULT_ERROR: {e}")

sabre_file = r'C:\Users\ARMANDO\travelhub_project\media\boletos_importados\2026\02\ZULUAGA_RIVILLAS_DIEGO_FERNANDO_MR_04MAY2025_CCS_IST.eml'
if os.path.exists(sabre_file):
    test_ai_parser(sabre_file)

import os
import django
import sys
import traceback

import logging

# Configurar logging para ver errores de apps y core
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.crm.services.whatsapp_bot_service import procesar_mensaje_entrante

def run_debug():
    print(f"DEBUG: GEMINI_API_KEY is {'SET' if os.environ.get('GEMINI_API_KEY') else 'NOT SET'}")
    print("INICIANDO DEBUG DE WHATSAPP BOT...")
    try:
        resultado = procesar_mensaje_entrante('584129998877', 'Elon Musk', 'Quiero viajar a Tokyo el proximo mes')
        print(f"RESULTADO: {resultado}")
    except Exception as e:
        print("ERROR FATAL EN DEBUG:")
        traceback.print_exc()

if __name__ == '__main__':
    run_debug()

import os
import django
import sys
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.services.ai_engine import ai_engine
from apps.crm.services.whatsapp_bot_service import AnalisisMensajeSchema, PROMPT_VENDEDOR_IA

def test():
    print("LLAMANDO A GEMINI...")
    try:
        raw = ai_engine.call_gemini(
            prompt="Mensaje: Quiero ir a Tokyo con 4 personas el proximo mes",
            response_schema=AnalisisMensajeSchema,
            system_instruction=PROMPT_VENDEDOR_IA
        )
        print(f"RAW KEYS: {list(raw.keys())}")
        print(f"RAW CONTENT: {json.dumps(raw, ensure_ascii=True)}")
        
        # Intentar validar
        print("VALIDANDO CON PYDANTIC...")
        obj = AnalisisMensajeSchema(**raw)
        print(f"OBJETO CREADO: {obj.es_solicitud_viaje}, {obj.destino}, {obj.pasajeros}")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    test()

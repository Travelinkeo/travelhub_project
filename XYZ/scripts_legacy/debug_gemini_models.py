
import google.generativeai as genai
import os
from django.conf import settings
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

api_key = getattr(settings, 'GEMINI_API_KEY', None)

if not api_key:
    print("❌ Eror: GEMINI_API_KEY no encontrada en settings")
else:
    print(f"✅ API Key encontrada: {api_key[:5]}...{api_key[-5:]}")
    genai.configure(api_key=api_key)
    
    print("\n🔍 Buscando modelos disponibles...")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"❌ Error listando modelos: {e}")

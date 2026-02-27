import google.generativeai as genai
import os

# Hardcode key for quick test if env is tricky, but try env first
api_key = os.environ.get('GEMINI_API_KEY')
# Load from .env manually just in case
if not api_key:
    try:
        with open('.env') as f:
            for line in f:
                if line.strip().startswith('GEMINI_API_KEY'):
                    api_key = line.split('=')[1].strip()
    except: pass

if api_key:
    genai.configure(api_key=api_key)
    print(f"API Key configurada (termina en {api_key[-4:]})")
    print("Listando modelos...")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"Error listando modelos: {e}")
else:
    print("NO API KEY FOUND")

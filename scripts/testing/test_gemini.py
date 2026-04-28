import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

print("Modelos disponibles:")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"- {model.name}")

# Probar con el primer modelo disponible
try:
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    response = model.generate_content("Hola, ¿cómo estás?")
    print(f"\nPrueba exitosa con gemini-1.5-flash-latest:")
    print(response.text)
except Exception as e:
    print(f"Error con gemini-1.5-flash-latest: {e}")
    
    try:
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        response = model.generate_content("Hola, ¿cómo estás?")
        print(f"\nPrueba exitosa con gemini-1.5-pro-latest:")
        print(response.text)
    except Exception as e2:
        print(f"Error con gemini-1.5-pro-latest: {e2}")
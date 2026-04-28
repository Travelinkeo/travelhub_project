import os
import google.generativeai as genai
from django.conf import settings
import sys

# Añadir el directorio del proyecto al path
sys.path.append('c:/Users/ARMANDO/travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')

from dotenv import load_dotenv
load_dotenv()

def list_models():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("No API Key found in env.")
        return
        
    genai.configure(api_key=api_key, transport="rest")
    print("Listing models:")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()

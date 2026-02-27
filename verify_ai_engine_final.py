import os
import sys
import json
import traceback
import google.generativeai as genai
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

# Configuración
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.0-flash"

class TestSchema(BaseModel):
    mensaje: str = Field(description="Un mensaje de saludo")
    exito: bool = Field(description="Indica si fue exitoso")

def run_diagnostic():
    print(f"\n{'='*50}")
    print("🔍 DIAGNÓSTICO FINAL: UNIVERSAL AI ENGINE")
    print(f"{'='*50}")
    
    print(f"1. API KEY: {'Present' if API_KEY else 'MISSING'}")
    if not API_KEY: return

    # Prueba 1: Conectividad Básica (gRPC vs REST)
    print("\n2. Probando Conectividad Básica (REST)...")
    try:
        genai.configure(api_key=API_KEY, transport="rest")
        model = genai.GenerativeModel(MODEL_NAME)
        res = model.generate_content("Hola, responde 'Conectado'.")
        print(f"   ✅ ÉXITO: {res.text.strip()}")
    except Exception as e:
        print(f"   ❌ FALLO REST: {e}")
        traceback.print_exc()

    # Prueba 2: Structured Output (Pydantic)
    print("\n3. Probando Structured Output (JSON Schema)...")
    try:
        config = {
            "response_mime_type": "application/json",
            "response_schema": TestSchema
        }
        res = model.generate_content("Saluda al usuario Armando.", generation_config=config)
        data = json.loads(res.text)
        print(f"   ✅ ÉXITO JSON: {data}")
    except Exception as e:
        print(f"   ❌ FALLO STRUCTURED OUTPUT: {e}")
        # Intentar sintaxis alternativa si falla (pasar esquema en constructor)
        print("\n   Probando sintaxis alternativa (esquema en GenerativeModel)...")
        try:
           model_alt = genai.GenerativeModel(
               model_name=MODEL_NAME,
               generation_config={"response_mime_type": "application/json", "response_schema": TestSchema}
           )
           res_alt = model_alt.generate_content("Saluda a Armando.")
           print(f"   ✅ ÉXITO SINTAXIS ALT: {res_alt.text}")
        except Exception as e2:
           print(f"   ❌ FALLO TOTAL: {e2}")
           traceback.print_exc()

if __name__ == "__main__":
    run_diagnostic()

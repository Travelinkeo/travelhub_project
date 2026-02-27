# import_tarifario_pdf.py
import os
import django
import json
import google.generativeai as genai
from decimal import Decimal
import time
from pypdf import PdfReader, PdfWriter

# Configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import (
    Moneda, HotelTarifario, TipoHabitacion, TarifaHabitacion, Amenity, TarifarioProveedor, Proveedor
)

PDF_PATH = r"C:\Users\ARMANDO\Downloads\TARIFARIO NACIONAL NOVIEMBRE 2025-013 (1).pdf"
API_KEY = os.getenv('GEMINI_API_KEY')
CHUNK_SIZE = 3  # Páginas por chunk para evitar timeouts/truncamiento

def clean_json_string(json_str):
    # Limpiar respuesta (Markdown code blocks)
    clean = json_str.replace('```json', '').replace('```', '').strip()
    return clean

def analyze_chunk(model, pdf_chunk_path, version):
    print(f"   📤 Subiendo chunk {version}...")
    sample_file = genai.upload_file(path=pdf_chunk_path, display_name=f"Tarifario Parte {version}")
    
    # Esperar procesamiento
    while sample_file.state.name == "PROCESSING":
        time.sleep(1)
        sample_file = genai.get_file(sample_file.name)
        
    if sample_file.state.name == "FAILED":
        print("   ❌ Falló el procesamiento del chunk.")
        return []

    prompt = """
    Act as a Data Extraction Agent. This document contains a list of hotels and their rates.
    
    TASK: Extract ALL hotels found in this specific document part.
    If a hotel spans across pages, do your best to extract what is visible.
    
    Return a JSON list of objects. Each object must have:
    - "hotel_name": Name of the hotel.
    - "destination": City or region (e.g., Margarita, Morrocoy, Los Roques, etc).
    - "category": Star rating (1-5), integer. Default to 3 if unknown.
    - "rooms": A list of room objects, each having:
        - "name": Room type name (e.g., Matrimonial, Doble, Triple).
        - "rate_dbl": Double occupancy rate (number).
        - "rate_sgl": Single occupancy rate (number, optional).
        - "currency": "USD" or "EUR".
    
    Clean the names. Remove extraneous text.
    Output ONLY valid JSON.
    Make sure to close the JSON array properly.
    If no hotels are found in this part, return an empty list [].
    """
    
    try:
        response = model.generate_content([sample_file, prompt])
        json_str = clean_json_string(response.text)
        data = json.loads(json_str)
        return data
    except Exception as e:
        print(f"   ⚠️ Error analizando chunk {version}: {e}")
        return []

def import_pdf():
    print(f"--- Iniciando Importación Inteligente de Tarifario PDF (Por Secciones) ---")
    
    if not os.path.exists(PDF_PATH):
        print("❌ Error: El archivo no existe.")
        return
    
    if not API_KEY:
        print("❌ Error: No se encontró GEMINI_API_KEY.")
        return

    # 1. Configurar Gemini
    genai.configure(api_key=API_KEY)
    
    # Identificar Modelo
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_name = next((m for m in available_models if 'flash' in m or '1.5' in m), available_models[0])
        print(f"🤖 Usando modelo: {model_name}")
        model = genai.GenerativeModel(model_name=model_name)
    except:
        model = genai.GenerativeModel(model_name="gemini-pro")

    # 2. Dividir PDF
    print("✂️  Dividiendo PDF en secciones...")
    reader = PdfReader(PDF_PATH)
    total_pages = len(reader.pages)
    print(f"   Total páginas: {total_pages}")
    
    all_hotels = []
    
    for i in range(0, total_pages, CHUNK_SIZE):
        writer = PdfWriter()
        end_page = min(i + CHUNK_SIZE, total_pages)
        
        for page_num in range(i, end_page):
            writer.add_page(reader.pages[page_num])
            
        chunk_filename = f"temp_chunk_{i}_{end_page}.pdf"
        with open(chunk_filename, "wb") as f:
            writer.write(f)
            
        print(f"\nProcessing Pages {i+1} to {end_page}...")
        chunk_data = analyze_chunk(model, chunk_filename, f"{i}-{end_page}")
        
        print(f"   ✅ Encontrados {len(chunk_data)} hoteles en esta sección.")
        all_hotels.extend(chunk_data)
        
        # Limpieza
        try:
            os.remove(chunk_filename)
        except:
            pass
            
    print(f"\n✨ Total Hoteles Encontrados: {len(all_hotels)}")

    # 4. Guardar en Base de Datos
    print("\n💾 Guardando en TravelHub...")
    usd, _ = Moneda.objects.get_or_create(codigo_iso="USD", defaults={"nombre": "Dólar"})
    
    proveedor_dummy, _ = Proveedor.objects.get_or_create(nombre="Importación Manual", defaults={"tipo_proveedor": "CON"})
    tarifario_obj, _ = TarifarioProveedor.objects.get_or_create(
        nombre="Tarifario Noviembre 2025 (Importado Completo)",
        proveedor=proveedor_dummy,
        defaults={
            "fecha_vigencia_inicio": "2025-11-01",
            "fecha_vigencia_fin": "2025-11-30"
        }
    )
    
    count_new = 0
    for item in all_hotels:
        try:
            # Crear Hotel
            hotel, created = HotelTarifario.objects.get_or_create(
                nombre=item['hotel_name'],
                defaults={
                    "destino": item.get('destination', 'Venezuela'),
                    "categoria": item.get('category', 3),
                    "tarifario": tarifario_obj,
                    "activo": True
                }
            )
            
            if created:
                count_new += 1
                print(f"   + Nuevo Hotel: {hotel.nombre}")
            else:
                print(f"   . Actualizando: {hotel.nombre}")
            
            # Crear Habitaciones y Tarifas
            for room_data in item.get('rooms', []):
                tipo_hab, _ = TipoHabitacion.objects.get_or_create(
                    hotel=hotel,
                    nombre=room_data['name']
                )
                
                TarifaHabitacion.objects.update_or_create(
                    tipo_habitacion=tipo_hab,
                    nombre_temporada="Nov-2025",
                    defaults={
                        "moneda": usd, 
                        "tarifa_dbl": Decimal(str(room_data.get('rate_dbl', 0))),
                        "tarifa_sgl": Decimal(str(room_data.get('rate_sgl', 0))),
                        "fecha_inicio": "2025-11-01",
                        "fecha_fin": "2025-11-30"
                    }
                )
        except Exception as e:
            print(f"⚠️ Error guardando hotel {item.get('hotel_name')}: {e}")
    
    print(f"\n✅ Importación completada. {count_new} hoteles nuevos creados.")

if __name__ == '__main__':
    import_pdf()

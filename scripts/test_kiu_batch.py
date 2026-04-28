import os
import django
import sys
import json
import logging
import time
from datetime import datetime
import email
from email import policy
from bs4 import BeautifulSoup
import re

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.kiu_parser import KIUParser
from core.ticket_parser import generate_ticket
from apps.bookings.models import BoletoImportado

# Configurar Logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

INPUT_DIR = r"C:\Users\ARMANDO\Downloads\Boletos\KIU"
OUTPUT_DIR = r"C:\Users\ARMANDO\travelhub_project\KIU_BATCH_OUTPUT"

def extract_text_from_eml(file_path):
    text_content = ""
    try:
        with open(file_path, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=policy.default)
            
        body = msg.get_body(preferencelist=('html', 'plain'))
        if body:
            content = body.get_content()
            if body.get_content_type() == 'text/html':
                soup = BeautifulSoup(content, 'html.parser')
                text_content = soup.get_text(separator=' ')
            else:
                text_content = content
        
        # Fallback: Walk parts if get_body fails or is complex
        if not text_content:
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    text_content += part.get_content()
                elif part.get_content_type() == "text/html":
                     soup = BeautifulSoup(part.get_content(), 'html.parser')
                     text_content += soup.get_text(separator=' ')

    except Exception as e:
        print(f"Error parsing EML {file_path}: {e}")
    return text_content

def run_kiu_test():
    print("--- INICIANDO TEST MASIVO KIU ---")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 Directorio de salida creado: {OUTPUT_DIR}")

    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(('.pdf', '.eml', '.txt', '.html'))]
    print(f"📄 Se encontraron {len(files)} archivos para procesar.")
    
    parser = KIUParser()
    results = []
    stats = {'success': 0, 'failed': 0, 'errors': 0}
    
    for idx, filename in enumerate(files):
        file_path = os.path.join(INPUT_DIR, filename)
        print(f"\n[{idx+1}/{len(files)}] 📂 Procesando: {filename}")
        
        try:
            # 1. Extraer Texto Robustamente
            text = ""
            if filename.lower().endswith('.pdf'):
                import fitz # PyMuPDF
                try:
                    with fitz.open(file_path) as doc:
                        for page in doc:
                            text += page.get_text()
                except Exception as e:
                    print(f"   ❌ Error leyendo PDF: {e}")
                    stats['errors'] += 1
                    continue
            elif filename.lower().endswith('.eml'):
                text = extract_text_from_eml(file_path)
            else:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                except Exception as e:
                     print(f"   ❌ Error leyendo archivo: {e}")
                     stats['errors'] += 1
                     continue

            if not text:
                print(f"   ⚠️ Texto vacío.")
                stats['errors'] += 1
                continue

            # 2. Parsear
            if not parser.can_parse(text):
                # print(f"   ⚠️ Parser KIU indica que NO puede parsear este archivo.")
                pass
            
            start_time = time.time()
            try:
                data = parser.parse(text)
                
                # Validaciones básicas
                is_valid = True
                missing = []
                if not data.passenger_name: missing.append("passenger_name")
                if not data.flights: missing.append("flights")
                if not data.fares.get('total_amount'): missing.append("total")
                
                if missing:
                    print(f"   ❌ Datos incompletos: {', '.join(missing)}")
                    stats['failed'] += 1
                    is_valid = False
                else:
                    print(f"   ✅ ÉXITO PARSEO ({time.time() - start_time:.2f}s)")
                    print(f"      Pax: {data.passenger_name}")
                    print(f"      Vuelos: {len(data.flights)}")
                    print(f"      Total: {data.fares.get('total_amount')} {data.fares.get('currency')}")
                    stats['success'] += 1

                # 3. Generar PDF (si es válido o parcialmente válido)
                if True: # Intentar generar PDF siempre para ver resultado visual
                    pdf_filename = f"PDF_{filename}.pdf"
                    pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)
                    
                    # Convertir a dict para generate_ticket
                    data_dict = data.to_dict()
                    
                    try:
                        # generate_ticket retorna (bytes, filename)
                        pdf_bytes, generated_name = generate_ticket(data_dict)
                        
                        if pdf_bytes:
                            with open(pdf_path, 'wb') as f:
                                f.write(pdf_bytes)
                            print(f"      📄 PDF Generado: {pdf_filename}")
                        else:
                            print(f"      ⚠️ generate_ticket retornó bytes vacíos.")
                            data_dict['pdf_error'] = "Empty bytes returned"
                            
                    except Exception as e:
                        print(f"      ⚠️ Falló generación PDF: {e}")
                        data_dict['pdf_error'] = str(e)
                
                # Guardar resultado
                res_entry = data.to_dict()
                res_entry['filename'] = filename
                res_entry['status'] = 'SUCCESS' if is_valid else 'PARTIAL'
                res_entry['missing_fields'] = missing
                results.append(res_entry)

            except Exception as e:
                print(f"   🔥 CRASH Parseo: {e}")
                stats['errors'] += 1
                results.append({'filename': filename, 'status': 'CRASH', 'error': str(e)})

        except Exception as e:
             print(f"   🔥 Error Global: {e}")
             stats['errors'] += 1

    # Resumen
    print("\n--- RESUMEN ---")
    print(f"Total Archivos: {len(files)}")
    print(f"✅ Exitosos: {stats['success']}")
    print(f"❌ Fallidos (Incompletos): {stats['failed']}")
    print(f"🔥 Errores (Crash/IO): {stats['errors']}")

    # Guardar JSON
    with open("KIU_BATCH_REPORT.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, default=str)
    
    print(f"\nReporte guardado en KIU_BATCH_REPORT.json")
    print(f"PDFs guardados en {OUTPUT_DIR}")

if __name__ == "__main__":
    run_kiu_test()

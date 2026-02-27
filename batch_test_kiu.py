import os
import io
import json
import logging
import traceback
import django
from typing import Dict, Any

# Configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.ticket_parser import extract_data_from_text, generate_ticket
from core.models import BoletoImportado
from django.core.files.base import ContentFile

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Rutas
SOURCE_DIR = r"C:\Users\ARMANDO\Downloads\Boletos\KIU"
OUTPUT_DIR = r"C:\Users\ARMANDO\travelhub_project\kiu_batch_tests"

def process_file(file_path: str):
    filename = os.path.basename(file_path)
    logger.info(f"--- Procesando: {filename} ---")
    
    try:
        # 1. Extraer texto
        texto_extraido = ""
        if filename.lower().endswith('.pdf'):
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    texto_extraido += (page.extract_text() or "") + "\n"
        elif filename.lower().endswith('.eml'):
            import eml_parser
            import datetime
            def json_serial(obj):
                if isinstance(obj, datetime.datetime):
                    return obj.isoformat()
                raise TypeError ("Type %s not serializable" % type(obj))

            with open(file_path, 'rb') as f:
                raw_email = f.read()
            
            ep = eml_parser.EmlParser(include_raw_body=True, include_attachment_data=True)
            parsed_eml = ep.decode_email_bytes(raw_email)
            
            # Intentar extraer de diferentes posibles campos de eml_parser
            if parsed_eml.get('body'):
                for b in parsed_eml['body']:
                    texto_extraido += b.get('content', '') + "\n"
            
            # Si sigue vacío, buscar en adjuntos (algunos boletos vienen como adjuntos html/txt)
            if not texto_extraido.strip() and parsed_eml.get('attachment'):
                for att in parsed_eml['attachment']:
                    if att.get('filename', '').lower().endswith(('.txt', '.html', '.htm', '.log')):
                         # Intentar decodificar el raw del adjunto si está disponible
                         # (Nota: eml_parser suele devolver base64 si no se procesa)
                         pass

            # Fallback manual para EML si eml_parser falla (lectura ruda)
            if not texto_extraido.strip():
                try:
                    texto_extraido = raw_email.decode('utf-8', errors='ignore')
                except:
                    texto_extraido = raw_email.decode('latin-1', errors='ignore')

        else:
            # Archivos de texto/log - Probar varios encodings
            for enc in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        texto_extraido = f.read()
                    if texto_extraido.strip(): break
                except:
                    continue

        if not texto_extraido.strip():
            logger.warning(f"⚠️ {filename}: No se pudo extraer texto legible.")
            return False

        # 2. Parsear con motor central (IA con fallback)
        # Usamos pdf_path si es PDF para que el parser de Copa u otros tengan acceso si es necesario
        pdf_path = file_path if filename.lower().endswith('.pdf') else None
        data = extract_data_from_text(texto_extraido, pdf_path=pdf_path)
        
        if not data or "error" in data:
            logger.error(f"❌ {filename}: Error en parseo -> {data.get('error') if data else 'Vació'}")
            return False

        # Normalización para reporte
        lista_tickets = []
        if isinstance(data, dict) and data.get('is_multi_pax'):
            lista_tickets = data.get('tickets', [])
        elif isinstance(data, list):
            lista_tickets = data
        else:
            lista_tickets = [data]

        for i, ticket_data in enumerate(lista_tickets):
            suffix = f"_{i}" if len(lista_tickets) > 1 else ""
            base_name = os.path.splitext(filename)[0] + suffix
            
            # 3. Guardar JSON
            json_path = os.path.join(OUTPUT_DIR, f"{base_name}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(ticket_data, f, indent=2, ensure_ascii=False)
            
            # 4. Generar PDF
            try:
                pdf_bytes, fname_pdf = generate_ticket(ticket_data)
                pdf_output_path = os.path.join(OUTPUT_DIR, f"{base_name}_GEN.pdf")
                with open(pdf_output_path, 'wb') as f:
                    f.write(pdf_bytes)
                logger.info(f"✅ {filename}: JSON y PDF generados con éxito ({ticket_data.get('SOURCE_SYSTEM')})")
            except Exception as e_pdf:
                logger.error(f"❌ {filename}: Error generando PDF -> {str(e_pdf)}")

        return True

    except Exception as e:
        logger.error(f"💥 {filename}: Fallo crítico -> {str(e)}")
        # print(traceback.format_exc())
        return False

from concurrent.futures import ThreadPoolExecutor

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    files = [f for f in os.listdir(SOURCE_DIR) if os.path.isfile(os.path.join(SOURCE_DIR, f))]
    logger.info(f"Encontrados {len(files)} archivos en KIU folder.")
    
    results = {"success": 0, "fail": 0}
    
    # Procesar en paralelo (máximo 5 hilos para no saturar Rate Limit)
    with ThreadPoolExecutor(max_workers=5) as executor:
        paths = [os.path.join(SOURCE_DIR, f) for f in files]
        outcomes = list(executor.map(process_file, paths))
        
    results["success"] = outcomes.count(True)
    results["fail"] = outcomes.count(False)
            
    logger.info(f"--- Fin del proceso ---")
    logger.info(f"Éxitos: {results['success']} | Fallos: {results['fail']}")

if __name__ == "__main__":
    main()

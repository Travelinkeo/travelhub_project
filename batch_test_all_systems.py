import os
import io
import json
import logging
import traceback
import django
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor

# Configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.ticket_parser import extract_data_from_text, generate_ticket
from core.models import BoletoImportado

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configuración de Rutas y Sistemas
SYSTEMS = {
    "SABRE": {
        "source": r"C:\Users\ARMANDO\Downloads\Boletos\SABRE",
        "output": r"C:\Users\ARMANDO\travelhub_project\sabre_batch_tests"
    },
    "AMADEUS": {
        "source": r"C:\Users\ARMANDO\Downloads\Boletos\AMADEUS",
        "output": r"C:\Users\ARMANDO\travelhub_project\amadeus_batch_tests"
    },
    "KIU": {
        "source": r"C:\Users\ARMANDO\Downloads\Boletos\KIU",
        "output": r"C:\Users\ARMANDO\travelhub_project\kiu_batch_tests"
    }
}

def extract_text(file_path: str) -> str:
    filename = os.path.basename(file_path)
    texto = ""
    try:
        if filename.lower().endswith('.pdf'):
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    texto += (page.extract_text() or "") + "\n"
        elif filename.lower().endswith('.eml'):
            import eml_parser
            with open(file_path, 'rb') as f:
                raw_email = f.read()
            ep = eml_parser.EmlParser(include_raw_body=True)
            parsed_eml = ep.decode_email_bytes(raw_email)
            if parsed_eml.get('body'):
                for b in parsed_eml['body']:
                    texto += b.get('content', '') + "\n"
            if not texto.strip():
                # Fallback manual para EML
                texto = raw_email.decode('utf-8', errors='ignore')
        else:
            for enc in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        texto = f.read()
                    if texto.strip(): break
                except:
                    continue
    except Exception as e:
        logger.error(f"Error extrayendo texto de {filename}: {e}")
    return texto

def process_file(file_info):
    file_path, output_dir, system_name = file_info
    filename = os.path.basename(file_path)
    
    try:
        texto = extract_text(file_path)
        if not texto.strip():
            return False, filename, "No text"

        # Parseo con motor Universal
        pdf_path = file_path if filename.lower().endswith('.pdf') else None
        data = extract_data_from_text(texto, pdf_path=pdf_path)
        
        if not data or "error" in data:
            return False, filename, data.get('error', 'Unknown parsing error')

        # Manejar multi-pax
        tickets = []
        if isinstance(data, dict) and data.get('is_multi_pax'):
            tickets = data.get('tickets', [])
        elif isinstance(data, list):
            tickets = data
        else:
            tickets = [data]

        success_pax = 0
        for i, t_data in enumerate(tickets):
            suffix = f"_{i}" if len(tickets) > 1 else ""
            base_name = os.path.splitext(filename)[0] + suffix
            
            # Guardar JSON
            json_path = os.path.join(output_dir, f"{base_name}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(t_data, f, indent=2, ensure_ascii=False)
            
            # Generar PDF
            try:
                pdf_bytes, _ = generate_ticket(t_data)
                pdf_path_out = os.path.join(output_dir, f"{base_name}_GEN.pdf")
                with open(pdf_path_out, 'wb') as f:
                    f.write(pdf_bytes)
                success_pax += 1
            except Exception as e_pdf:
                logger.warning(f"Error PDF para {filename}: {e_pdf}")

        return True, filename, f"AI System: {data.get('SOURCE_SYSTEM', 'Unknown')}"

    except Exception as e:
        return False, filename, str(e)

def main():
    total_results = {}
    
    for sys_name, paths in SYSTEMS.items():
        source = paths["source"]
        output = paths["output"]
        
        if not os.path.exists(source):
            logger.warning(f"Saltando {sys_name}: Carpeta no encontrada en {source}")
            continue
            
        if not os.path.exists(output):
            os.makedirs(output)
            
        files = [f for f in os.listdir(source) if os.path.isfile(os.path.join(source, f))]
        logger.info(f"==> Iniciando {sys_name} ({len(files)} archivos)")
        
        file_tasks = [(os.path.join(source, f), output, sys_name) for f in files]
        
        results = {"success": 0, "fail": 0, "details": []}
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            outcomes = list(executor.map(process_file, file_tasks))
            
        for ok, fname, msg in outcomes:
            if ok:
                results["success"] += 1
            else:
                results["fail"] += 1
            results["details"].append(f"{fname} | {msg}")
            
        total_results[sys_name] = results
        logger.info(f"Fin {sys_name}: {results['success']} OK, {results['fail']} ERROR")

    # Guardar reporte consolidado
    with open("gds_batch_report.json", "w", encoding="utf-8") as rf:
        json.dump(total_results, rf, indent=2)
    
    logger.info("Reporte consolidado generado: gds_batch_report.json")

if __name__ == "__main__":
    main()

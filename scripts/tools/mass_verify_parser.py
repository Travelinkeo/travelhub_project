
import os
import json
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.ticket_parser import extract_data_from_text

BASE_DIR = r"C:\Users\ARMANDO\Downloads\Boletos"
folders = ["SABRE", "COPA", "KIU", "AVIOR", "ESTELAR", "RUTACA", "WINGO", "TK CONNECT"]

def run_test():
    report = []
    
    for folder in folders:
        folder_path = os.path.join(BASE_DIR, folder)
        if not os.path.exists(folder_path):
            print(f"Skipping {folder}: Path not found")
            continue
            
        # Get first 2 files (PDF or EML)
        files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.pdf', '.eml'))][:2]
        
        for filename in files:
            file_path = os.path.join(folder_path, filename)
            print(f"Parsing: {folder}/{filename}...")
            
            try:
                # Reading text for quick log
                text = ""
                if filename.lower().endswith('.pdf'):
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        for page in pdf.pages:
                            text += (page.extract_text() or "") + "\n"
                else:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()

                # Call real parser
                res = extract_data_from_text(text, pdf_path=file_path)
                
                status = "✅ OK" if res and "error" not in res else "❌ FAIL"
                error = res.get('error') if res else 'None'
                
                report.append({
                    "system": folder,
                    "file": filename,
                    "status": status,
                    "error": error,
                    "pnr": res.get("CODIGO_RESERVA") if res else None,
                    "airline_pnr": res.get("CODIGO_RESERVA_AEROLINEA") if res else None,
                    "ticket": res.get("NUMERO_DE_BOLETO") if res else None,
                    "flights_count": len(res.get("vuelos", [])) if res else 0
                })
            except Exception as e:
                report.append({
                    "system": folder,
                    "file": filename,
                    "status": "🔥 ERROR",
                    "error": str(e)
                })

    # Print Summary Table
    print("\n" + "="*80)
    print(f"{'SISTEMA':<12} | {'SITUACIÓN':<10} | {'GDS PNR':<10} | {'AIRLINE PNR':<12} | {'VUELOS':<6}")
    print("-" * 80)
    for r in report:
        print(f"{r['system']:<12} | {r['status']:<10} | {str(r.get('pnr')):<10} | {str(r.get('airline_pnr')):<12} | {r.get('flights_count', 0)}")
    print("="*80)

if __name__ == "__main__":
    run_test()


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
            continue
            
        files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.pdf', '.eml'))][:2]
        
        for filename in files:
            file_path = os.path.join(folder_path, filename)
            
            try:
                # Reading text
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
                
                report.append({
                    "system": folder,
                    "file": filename,
                    "status": status,
                    "pnr": res.get("CODIGO_RESERVA") if res else None,
                    "airline_pnr": res.get("CODIGO_RESERVA_AEROLINEA") if res else None,
                    "passenger": res.get("NOMBRE_DEL_PASAJERO") if res else None,
                    "flights": [f"{v['numero_vuelo']} ({v['origen']}->{v['destino']})" for v in res.get("vuelos", [])] if res else []
                })
            except Exception as e:
                report.append({
                    "system": folder,
                    "file": filename,
                    "status": "🔥 ERROR",
                    "error": str(e)
                })

    with open("parsing_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("Report saved to parsing_report.json")

if __name__ == "__main__":
    run_test()


import os
import sys
import glob
import django
import tabulate

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.gemini_parser import GeminiParser
import pdfplumber

FIXTURES_DIR = os.path.join(os.getcwd(), 'core', 'tests', 'fixtures')

def extract_text(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    except Exception as e:
        return f"ERROR: {e}"
    return text

def main():
    print(f"🛡️  GUARDIAN: Iniciando pruebas de regresión en {FIXTURES_DIR}")
    
    pdf_files = glob.glob(os.path.join(FIXTURES_DIR, "*.pdf"))
    if not pdf_files:
        print("❌ No se encontraron archivos PDF en la carpeta de fixtures.")
        return

    parser = GeminiParser()
    results = []

    print(f"📂 Encontrados {len(pdf_files)} archivos. Procesando con GEMINI AI 🤖...\n")

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        # print(f"   > Procesando: {filename}...")
        
        text = extract_text(pdf_path)
        if text.startswith("ERROR"):
            results.append([filename, "ERROR", 0, "N/A", text])
            continue
            
        try:
            # Check if parser accepts it
            if not parser.can_parse(text):
                results.append([filename, "SKIP", 0, "N/A", "No detectado como Sabre"])
                continue

            data = parser.parse(text)
            
            # Handle list vs parsed data object
            if isinstance(data, dict):
                flights = data.get('vuelos', [])
                pnr = data.get('pnr', 'N/A')
            else:
                flights = getattr(data, 'flights', []) or getattr(data, 'vuelos', [])
                pnr = getattr(data, 'pnr', 'N/A')

            # Analyze first flight for quick check
            first_flight_summ = ""
            if flights:
                f1 = flights[0]
                orig = f1.get('origen', {}).get('ciudad', 'N/A')
                dest = f1.get('destino', {}).get('ciudad', 'N/A')
                airline = f1.get('aerolinea', 'N/A')
                first_flight_summ = f"{airline} | {orig}->{dest}"
            
            # Heuristics for status
            if len(flights) > 0:
                status = "✅ OK"
                details = first_flight_summ
            else:
                if len(text) < 100:
                    status = "⚠️ IMAGEN?"
                    details = "Texto < 100 chars. Posible escaneo."
                else:
                    status = "⚠️ VACÍO" 
                    details = "Texto detectado pero sin vuelos."

            results.append([filename, status, len(flights), pnr, details])
            
        except Exception as e:
             results.append([filename, "💥 CRASH", 0, "N/A", str(e)])

    # Print Table
    headers = ["Archivo", "Estado", "Vuelos", "PNR", "Detalle 1er Vuelo"]
    print(tabulate.tabulate(results, headers=headers, tablefmt="grid"))
    
    print("\n✅ Pruebas finalizadas.")

if __name__ == "__main__":
    main()

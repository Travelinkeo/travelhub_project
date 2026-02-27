import sys
import os
import django
import pdfplumber
import re

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.sabre_parser import SabreParser

def analyze_sabre_pdfs():
    import glob
    
    # File logging because console pipe is flaky
    log_file = open('sabre_output_full.txt', 'w', encoding='utf-8')
    try:
        def log_print(msg):
            # Still print to console for liveness
            print(msg, flush=True)
            log_file.write(str(msg) + '\n')
            log_file.flush() # Force write
            
        base_dir = r"C:\Users\ARMANDO\Downloads"
        # Match ONLY the original PDF now
        pattern = os.path.join(base_dir, "Re_ Solicitud de emisi*SABRE*", "*11 marzo*.pdf")
        files = glob.glob(pattern)
        
        if not files:
            log_print(f"No files found with pattern: {pattern}")
            # Try broader search
            files = glob.glob(os.path.join(base_dir, "*11 marzo*.pdf"))

        log_print(f"Found {len(files)} files to analyze.")
        
        parser = SabreParser()
        
        for fpath in files:
            log_print(f"\nProcessing: {os.path.basename(fpath)}")
            
            text = ""
            try:
                log_print("  Opening PDF...")
                with pdfplumber.open(fpath) as pdf:
                    log_print(f"  PDF Opened. Pages: {len(pdf.pages)}")
                    for i, page in enumerate(pdf.pages):
                        log_print(f"  Extracting page {i+1}...")
                        extracted = page.extract_text()
                        log_print(f"  Page {i+1} extracted bytes: {len(extracted) if extracted else 0}")
                        text += (extracted or "") + "\n"
                log_print("  PDF Extraction Complete.")
            except Exception as e:
                log_print(f"Error reading PDF: {e}")
                import traceback
                traceback.print_exc(file=log_file)
                continue
                
            log_print(f"Text Length: {len(text)}")
            
            # DEBUG: PRINT FULL TEXT (Short file)
            log_print("--- FULL PDF TEXT ---")
            log_print(text)
            log_print("---------------------")
            
            # DEBUG: PRINT RAW FLIGHT SECTION (Legacy check)
            vuelo_section_match = re.search(r'(?:Información [Dd]e Vuelo|Flight Information)(.*?)(?:Detalles [Dd]e Pago|Payment Details|Aviso:|Notice:)', text, re.DOTALL | re.IGNORECASE)
            if vuelo_section_match:
                vuelo_text = vuelo_section_match.group(1)
                log_print("--- FLIGHT SECTION HEAD ---")
                log_print(vuelo_text[:400]) 
                log_print("--- FLIGHT SECTION TAIL ---")
                log_print(vuelo_text[-400:]) 
                
                # DEBUG SPLIT
                primary_blocks = re.split(r'(?:This is not a boarding pass|Esta no es una tarjeta de embarque|Preparado para)', vuelo_text, flags=re.IGNORECASE)
                log_print(f"Primary Blocks: {len(primary_blocks)}")
                for pb in primary_blocks:
                    if not pb.strip(): continue
                    # The regex I added to the parser:
                    regex = r'((?:\n|^)(?:Salida:\s*)?\s*\d{1,2}\s*[a-zA-Z]{3,}\s*\d{2,4})'
                    splits = re.split(regex, pb, flags=re.IGNORECASE)
                    log_print(f"  > Split count with regex: {len(splits)}")
                    for k, s in enumerate(splits):
                        log_print(f"    Seg {k}: {s[:100].replace(chr(10), 'NL')}")
            else:
                 log_print("[FAIL] No Flight Section Found via Regex")

            try:
                parsed = parser.parse(text)
                flights = parsed.flights
                log_print(f"  > PNR: {parsed.pnr}")
                log_print(f"  > Flight Count: {len(flights)}")
                
                for i, f in enumerate(flights):
                     log_print(f"    [Flight {i+1}]")
                     log_print(f"      - Date: {f.get('fecha_salida')} / {f.get('fecha_llegada')}")
                     log_print(f"      - Route: {f.get('origen')} -> {f.get('destino')}")
                     log_print(f"      - Raw Block Snippet: {f.get('aerolinea')} {f.get('numero_vuelo')}")

            except Exception as e:
                log_print(f"  [CRASH] {e}")
                import traceback
                traceback.print_exc(file=log_file)
    finally:
        log_file.close()

if __name__ == '__main__':
    analyze_sabre_pdfs()

if __name__ == '__main__':
    analyze_sabre_pdfs()

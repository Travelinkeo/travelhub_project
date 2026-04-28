
import os
import django
import sys
import pdfplumber
import re

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models_catalogos import Aerolinea

def clean_text(text):
    if not text: return ""
    return text.replace('\n', ' ').strip()

def run():
    file_path = r"C:\Users\ARMANDO\Downloads\Tabla Mundial de Aerolíneas.pdf"
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    print(f"--- Processing {file_path} ---")
    
    count_updated = 0
    count_created = 0
    count_skipped = 0
    
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            if not tables:
                continue
            
            print(f"Page {i+1}: Found {len(tables)} tables.")
            
            for table in tables:
                for row in table:
                    # Expecting at least 3 columns: Name, IATA, Numeric
                    # Row might be: ['Air Canada', 'AC', '014', 'Address...', 'Altéa']
                    
                    # Filter empty rows
                    if not row or not any(row):
                        continue
                        
                    # Basic validation of structure
                    # Name is usually col 0
                    # IATA is usually col 1 (2 chars)
                    # Numeric is usually col 2 (3 digits)
                    
                    # Heuristic: Find the 2-char column and 3-digit column
                    name = ""
                    iata = ""
                    numeric = ""
                    
                    clean_row = [clean_text(c) for c in row if c]
                    
                    # Attempt to identify columns by pattern
                    # Pattern for IATA: ^[A-Z0-9]{2}$
                    # Pattern for Numeric: ^\d{3}$
                    
                    candidate_iata_idx = -1
                    candidate_num_idx = -1
                    
                    for idx, cell in enumerate(clean_row):
                        if re.match(r'^[A-Z0-9]{2}$', cell):
                            candidate_iata_idx = idx
                        if re.match(r'^\d{3}$', cell):
                            candidate_num_idx = idx
                            
                    # Robustness: strict indices if table is well-formed
                    # Based on snippet: Name(0), IATA(1), Numeric(2) matches nicely
                    if len(row) >= 3:
                         raw_name = clean_text(row[0])
                         raw_iata = clean_text(row[1])
                         raw_num = clean_text(row[2])
                         
                         if re.match(r'^[A-Z0-9]{2}$', raw_iata) and re.match(r'^\d{3}$', raw_num):
                             name = raw_name
                             iata = raw_iata
                             numeric = raw_num
                    
                    # Fallback to search if strict position failed
                    if not iata and candidate_iata_idx != -1 and candidate_num_idx != -1:
                        iata = clean_row[candidate_iata_idx]
                        numeric = clean_row[candidate_num_idx]
                        # Name is likely the longest string or first string
                        # Let's assume Name is col 0
                        if candidate_iata_idx > 0:
                            name = clean_row[0]
                            
                    if not iata or not numeric:
                        count_skipped += 1
                        continue
                        
                    # Skip Headers
                    if iata == "IATA" or numeric == "Cód":
                        continue
                        
                    print(f"   Importing: [{iata}] {name} ({numeric})")
                    
                    try:
                        # Smart Update
                        qs = Aerolinea.objects.filter(codigo_iata=iata)
                        if qs.exists():
                            obj = qs.first()
                            # Only update if name is better (longer?) or if we want to overwrite
                            # Let's overwrite Name and Numeric
                            obj.nombre = name if len(name) > len(obj.nombre) else obj.nombre
                            obj.codigo_numerico = numeric # Always take numeric from this authoritative PDF
                            obj.activa = True
                            obj.save()
                            count_updated += 1
                            # Deduplicate if needed
                            if qs.count() > 1:
                                qs.exclude(pk=obj.pk).delete()
                        else:
                            Aerolinea.objects.create(
                                codigo_iata=iata,
                                codigo_numerico=numeric,
                                nombre=name,
                                activa=True
                            )
                            count_created += 1
                            
                    except Exception as e:
                        print(f"Error saving {iata}: {e}")

    print(f"\n--- Done. Created: {count_created}, Updated: {count_updated}, Skipped: {count_skipped} ---")

if __name__ == "__main__":
    run()

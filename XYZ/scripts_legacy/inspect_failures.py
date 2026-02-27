import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado

def inspect_failures():
    print("--- INSPECTING RECENT TICKET FAILURES ---")
    count = BoletoImportado.objects.count()
    print(f"Total boletos: {count}")
    
    # Get last 5 tickets by ID
    boletos = BoletoImportado.objects.order_by('-id_boleto_importado')[:5]
    
    for b in boletos:
        print(f"\n---------------")
        print(f"ID: {b.pk} | File: {b.archivo_boleto.name}")
        print(f"Fecha: {b.fecha_subida}")
        print(f"Status: {b.estado_parseo}")
        
        log_snippet = b.log_parseo[:1000] if b.log_parseo else "No Log"
        print(f"Log start: {log_snippet}")
        
        if b.datos_parseados:
            import json
            print(f"Datos Parseados Keys: {list(b.datos_parseados.keys())}")
            print(f"GDS: {b.datos_parseados.get('gds_detected')}")
            print(f"Source System: {b.datos_parseados.get('SOURCE_SYSTEM')}")
        else:
            print("Datos Parseados: None")

        # Check path
        if b.pk == 424 and b.archivo_boleto:
            try:
                import pdfplumber
                # Construct absolute path assuming media root structure
                base_dir = r"C:\Users\ARMANDO\travelhub_project"
                rel_path = b.archivo_boleto.name
                # Try simple join first (if using FileSystemStorage default)
                full_path = os.path.join(base_dir, "media", rel_path) # Assuming media is in project root
                if not os.path.exists(full_path):
                     full_path = os.path.join(base_dir, rel_path) # Maybe relative to root?
                
                print(f"Attempting extraction from: {full_path}")
                if os.path.exists(full_path):
                    with pdfplumber.open(full_path) as pdf:
                        text = pdf.pages[0].extract_text()
                        print("\n--- TEXT EXTRACT (First 1000 chars) ---")
                        print(text[:1000])
                        print("---------------------------------------")
                else:
                    print("❌ File not found on disk.")
            except Exception as e:
                print(f"❌ Extraction error: {e}")


if __name__ == "__main__":
    inspect_failures()


import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models_catalogos import Aerolinea

def run():
    # Data format: "NUMERIC-IATA-NAME"
    kiu_airlines_raw = """
765-5R-RUTACA
185-7N-PAWA DOMINICANA
805-7P-AIR PANAMA
019-9R-SATENA
742-9V-AVIOR AIRLINES C A
312-CV-AEROCARIBE
159-CW-AEROPOSTAL ALAS DE VENEZUELA CA
791-DO-SKY HIGH
052-ES-ESTELAR
660-G0-ALIANZA GLANCELOT C A
402-G6-GLOBAL
804-GI-FLY THE WORLD
377-L5-RED AIR
921-O3-SASCA AIRLINES
663-PU-PLUS ULTRA
782-QL-LASER AIRLINES
382-T7-SKY ATLANTIC TRAVEL US.
067-T9-TURPIAL AIRLINES CA
308-V0-CONVIASA
364-WW-RUTAS AEREAS DE VENEZUELA
"""
    
    lines = [L.strip() for L in kiu_airlines_raw.split('\n') if L.strip()]
    
    print(f"--- Updating Airline Catalog with {len(lines)} KIU Entries ---")
    
    for line in lines:
        try:
            parts = line.split('-')
            if len(parts) < 3:
                print(f"⚠️ Formato inválido: {line}")
                continue
                
            code_num = parts[0].strip()
            code_iata = parts[1].strip()
            # Name might contain hyphens, join the rest
            full_name = '-'.join(parts[2:]).strip()
            
            # Clean name
            clean_name = full_name
            # Remove boring suffixes
            for suffix in [" C A", " CA", " S.A.", " SA", " C.A."]:
                if clean_name.endswith(suffix):
                    clean_name = clean_name[:-len(suffix)]
            
            clean_name = clean_name.strip()

            print(f"Processing: [{code_iata}] {clean_name} (Plate: {code_num})")
            
            # Smart Update with Deduplication
            qs = Aerolinea.objects.filter(codigo_iata=code_iata)
            if qs.exists():
                if qs.count() > 1:
                    print(f"   ⚠️ Duplicate entries found for {code_iata}. Cleaning up...")
                    # Keep the one with similar name or first one
                    first_obj = qs.first()
                    duplicates = qs.exclude(pk=first_obj.pk)
                    count_deleted = duplicates.count()
                    duplicates.delete()
                    print(f"      Deleted {count_deleted} duplicates.")
                    obj = first_obj
                else:
                    obj = qs.first()
                
                # Update fields
                obj.nombre = clean_name
                obj.codigo_numerico = code_num
                obj.activa = True
                obj.save()
                created = False
            else:
                # Create new
                obj = Aerolinea.objects.create(
                    codigo_iata=code_iata,
                    nombre=clean_name,
                    codigo_numerico=code_num,
                    activa=True
                )
                created = True
            
            action = "Created" if created else "Updated"
            print(f"   ✅ {action}: {obj}")
            
        except Exception as e:
            print(f"   ❌ Error processing {line}: {e}")

    # Also make sure major airlines are present (from previous knowledge context)
    # Just in case they are missing
    
    print("\n--- Done ---")

if __name__ == "__main__":
    run()

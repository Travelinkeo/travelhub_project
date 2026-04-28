import os
import sys
import re
import json
import django

# Setup path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.amadeus_parser import AmadeusParser

DUMP_FILE = 'XYZ/amadeus_samples/analysis_dump.txt'

def main():
    if not os.path.exists(DUMP_FILE):
        print("❌ Dump file not found.")
        return

    print("🚀 Iniciando Verificación de Consolidación Amadeus [100%]...")
    
    with open(DUMP_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    sections = re.split(r'={50}\nFILE: (.+?)\n={50}\n', content)
    parser = AmadeusParser()
    
    success_count = 0
    total_samples = (len(sections) - 1) // 2
    
    for i in range(1, len(sections), 2):
        filename = sections[i]
        text = sections[i+1]
        
        print(f"\n📄 Analizando: {filename}")
        try:
            parsed = parser.parse(text)
            data = parsed.to_dict()
            
            pnr = data.get('pnr')
            vuelos = len(data.get('vuelos', []))
            pasajero = data.get('pasajero', {}).get('nombre_completo')
            
            status = "✅" if pnr != 'No encontrado' and vuelos > 0 else "❌"
            if status == "✅": success_count += 1
            
            print(f"{status} PNR: {pnr}")
            print(f"   Vuelos: {vuelos}")
            print(f"   Pasajero: {pasajero}")
            print(f"   Total: {data.get('total')}")
            
        except Exception as e:
            print(f"💥 Error: {e}")

    print(f"\n--- Resumen Final ---")
    print(f"Promedio de éxito: {success_count}/{total_samples} ({success_count/total_samples*100:.1f}%)")
    
    if success_count == total_samples:
        print("🎉 ¡CONSOLIDACIÓN EXITOSA! 100% de cobertura alcanzada.")
    else:
        print("⚠️ Aún quedan detalles por pulir.")

if __name__ == "__main__":
    main()

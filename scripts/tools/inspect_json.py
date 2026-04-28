import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import BoletoImportado

def inspect_last_boleto_json():
    b = BoletoImportado.objects.order_by('-id_boleto_importado').first()
    if not b:
        print("No boletos found.")
        return
        
    print(f"Boleto ID: {b.id_boleto_importado}")
    print(f"Localizador: {b.localizador_pnr}")
    print(f"Pax: {b.nombre_pasajero_completo}")
    print(f"IATA (DB Field Agent): {b.agente_emisor}")
    
    if b.datos_parseados:
        # Check normalized block
        norm = b.datos_parseados.get('normalized', b.datos_parseados)
        print("\n--- Normalized Data (JSON) ---")
        print(json.dumps(norm, indent=2))
        
        if 'NUMERO_IATA' in norm:
            print(f"\n✅ NUMERO_IATA Found: {norm['NUMERO_IATA']}")
        else:
            print("\n❌ NUMERO_IATA Missing in normalized data.")
            
        if 'SOURCE_SYSTEM' in norm:
            print(f"✅ SOURCE_SYSTEM Found: {norm['SOURCE_SYSTEM']}")
            
    else:
        print("No datos_parseados found.")

if __name__ == '__main__':
    inspect_last_boleto_json()

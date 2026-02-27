
import os
import sys
import django
from django.conf import settings
import json

# Setup Django
sys.path.append('c:\\Users\\ARMANDO\\travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado

def list_latest():
    print("--- Latest 5 Imported Tickets ---")
    boletos = BoletoImportado.objects.all().order_by('-fecha_subida')[:10]
    for b in boletos:
        print(f"ID: {b.pk} | Created: {b.fecha_subida} | File: {b.archivo_boleto.name}")
        print(f"   Status: {b.get_estado_parseo_display()}")
        if b.datos_parseados:
            data = b.datos_parseados
            src = data.get('SOURCE_SYSTEM', 'UNKNOWN')
            p_name = data.get('NOMBRE_DEL_PASAJERO', 'N/A')
            print(f"   System: {src} | Passenger: {str(p_name).encode('ascii', 'ignore').decode('ascii')}")
            
            flights = data.get('vuelos', [])
            print(f"   Flights: {len(flights)}")
            for f in flights:
                print(f"      - {f.get('origen')} -> {f.get('destino')} ({f.get('numero_vuelo')})")
        else:
            print("   No parsed data.")
        print("-" * 40)

if __name__ == "__main__":
    list_latest()

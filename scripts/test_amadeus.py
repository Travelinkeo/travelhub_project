
import os
import sys
import django
import asyncio

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.services.amadeus_service import AmadeusService

def test_amadeus():
    print("🌍 Iniciando prueba de Amadeus API...")
    
    service = AmadeusService()
    
    # Fecha futura (ajustar según fecha actual)
    origin = "CCS"
    destination = "MAD"
    date = "2026-02-15" 
    
    print(f"🔎 Buscando: {origin} -> {destination} ({date})")
    
    try:
        results = service.buscar_vuelos(origin, destination, date)
        
        if isinstance(results, dict) and 'error' in results:
            print(f"❌ Error API: {results['error']}")
        elif not results:
            print("⚠️ No se encontraron resultados (puede ser normal por disponibilidad/fecha).")
        else:
            print(f"✅ Éxito! Se encontraron {len(results)} ofertas.")
            for i, r in enumerate(results[:3], 1):
                print(f"   {i}. {r['aerolinea']} - {r['precio']} ({r['ruta']})")
                
    except Exception as e:
        print(f"💥 Excepción crítica: {e}")

if __name__ == "__main__":
    test_amadeus()

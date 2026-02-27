
import os
import sys

# Setup Django path FIRST
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')

import django
django.setup()

from core.services.amadeus_service import AmadeusService
import json

def debug_search():
    print("--- Probando Amadeus Service (Depuración) ---")
    service = AmadeusService()
    
    # Parámetros que fallaron (CCS-BOG puede no estar en Sandbox)
    # Probamos una ruta "segura" de Amadeus Sandbox
    origin = "MAD"
    destination = "JFK"
    date = "2026-03-13" 
    
    print(f"Buscando: {origin} -> {destination} en {date} (Ruta de Prueba)")
    
    # Verificar credenciales (sin mostrar secret completo)
    client_id = os.getenv('AMADEUS_CLIENT_ID')
    client_secret = os.getenv('AMADEUS_CLIENT_SECRET')
    print(f"Client ID: {client_id[:4]}...{client_id[-4:] if client_id else 'None'}")
    print(f"Client Secret: {'Presente' if client_secret else 'Faltante'}")

    try:
        # Llamar directamente a la API interna para ver excepciones
        response = service.amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=date,
            adults=1,
            max=1
        )
        print("✅ Éxito:")
        print(json.dumps(response.data, indent=2))
    except Exception as e:
        print(f"\n❌ Error Capturado: {e}")
        if hasattr(e, 'response'):
             print(f"Status Code: {e.response.status_code}")
             print("📄 Data/Body del Error:")
             print(e.response.body)
             # A veces el error detallado esta en 'data' if parsed
             if hasattr(e.response, 'data'):
                 print("📄 Data Parseada:")
                 print(e.response.data)

if __name__ == "__main__":
    debug_search()

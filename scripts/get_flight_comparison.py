
import os
import json
from amadeus import Client, ResponseError

def load_env_manually():
    env_path = os.path.join(os.getcwd(), '.env')
    if not os.path.exists(env_path): return
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v

def get_comparison_flight():
    load_env_manually()
    
    amadeus = Client(
        client_id=os.environ.get('AMADEUS_CLIENT_ID'),
        client_secret=os.environ.get('AMADEUS_CLIENT_SECRET'),
        hostname='test'
    )
    
    # Probamos varias fechas para ver si alguna "pega"
    dates_to_test = [
        '2025-02-28', # ~1 mes desde "hoy" (asumiendo 2025)
        '2025-06-15', # ~6 meses
        '2025-11-20', # ~10 meses
    ]
    
    for date in dates_to_test:
        print(f"\n--- Probando Fecha: {date} (MAD-JFK) ---")
        try:
            response = amadeus.shopping.flight_offers_search.get(
                originLocationCode='MAD',
                destinationLocationCode='JFK',
                departureDate=date,
                adults=1,
                max=1
            )
            
            print(f"✅ ¡ÉXITO con {date}!")
            data = response.data[0]
            print(f"   Precio: {data['price']['total']} {data['price']['currency']}")
            # Si uno funciona, paramos
            break
            
        except ResponseError as error:
            print(f"❌ Error con {date}: {error.response.status_code}")
            if error.response.body:
                print(f"   Body: {error.response.body}")
        except Exception as e:
            print(f"❌ Error General: {e}")

if __name__ == "__main__":
    get_comparison_flight()

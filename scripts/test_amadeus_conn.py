
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

def test_connectivity():
    load_env_manually()
    
    try:
        amadeus = Client(
            client_id=os.environ.get('AMADEUS_CLIENT_ID'),
            client_secret=os.environ.get('AMADEUS_CLIENT_SECRET'),
            hostname='test'
        )
        
        print("1. Probando Referencia de Datos (Locations)...")
        response = amadeus.reference_data.locations.get(
            keyword='MAD',
            subType='CITY'
        )
        print("✅ Conectividad OK. Datos recibidos:")
        print(f"   Nombre: {response.data[0]['name']}")
        print(f"   IATA: {response.data[0]['iataCode']}")
        
        return True
    
    except ResponseError as error:
        print(f"❌ Error Conectividad: {error}")
        print(f"   {error.response.body}")
        return False
    except Exception as e:
        print(f"❌ Error General: {e}")
        return False

if __name__ == "__main__":
    test_connectivity()

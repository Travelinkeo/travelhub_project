
import os
import json
from amadeus import Client, ResponseError

def load_env_manually():
    """Simple parser for .env file to avoid dependencies"""
    env_path = os.path.join(os.getcwd(), '.env')
    if not os.path.exists(env_path):
        print("❌ .env not found")
        return
        
    print("Reading .env...")
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

def test_amadeus():
    load_env_manually()
    
    client_id = os.environ.get('AMADEUS_CLIENT_ID')
    client_secret = os.environ.get('AMADEUS_CLIENT_SECRET')
    
    print(f"Client: {client_id[:4]}... / Secret: {'Yes' if client_secret else 'No'}")
    
    if not client_id or not client_secret:
        print("❌ Missing Credentials")
        return

    try:
        amadeus = Client(
            client_id=client_id,
            client_secret=client_secret,
            hostname='test' # Sandbox
        )
        
        print("\n--- Testing Flight Search (LHR-CDG) ---")
        # Probamos una fecha muy cercana y una ruta europea simple
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode='LHR',
            destinationLocationCode='CDG',
            departureDate='2025-02-01', 
            adults=1,
            max=1
        )
        print("✅ Success!")
        # print(json.dumps(response.data, indent=2)) 

    except ResponseError as error:
        print(f"\n❌ Error Amadeus: {error}")
        print(f"Status: {error.response.status_code}")
        print("📄 Response Body:")
        print(error.response.body)
    except Exception as e:
        print(f"❌ General Error: {e}")

if __name__ == "__main__":
    test_amadeus()

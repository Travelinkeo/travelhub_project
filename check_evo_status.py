import requests
import json

BASE_URL = "http://localhost:8085"
API_KEY = "TravelHubSecretKey2026"

headers = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

def check_status():
    print("--- Estado de Instancias en Evolution API ---")
    try:
        resp = requests.get(f"{BASE_URL}/instance/fetchInstances", headers=headers, timeout=10)
        instances = resp.json()
        print(json.dumps(instances, indent=2))
        
        for inst in instances:
            name = inst.get('name')
            print(f"\nVerificando conexión para: {name}")
            conn_resp = requests.get(f"{BASE_URL}/instance/connectionState/{name}", headers=headers, timeout=10)
            print(f"Estado de conexión: {conn_resp.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_status()

import requests

BASE_URL = "http://localhost:8085"
API_KEY = "TravelHubSecretKey2026"

headers = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

def purge_all():
    print("--- Purgando TODAS las instancias ---")
    try:
        resp = requests.get(f"{BASE_URL}/instance/fetchInstances", headers=headers, timeout=10)
        instances = resp.json()
        
        for inst in instances:
            name = inst.get('name')
            print(f"Eliminando: {name}")
            requests.delete(f"{BASE_URL}/instance/logout/{name}", headers=headers)
            requests.delete(f"{BASE_URL}/instance/delete/{name}", headers=headers)
            
        print("Purga completada.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    purge_all()

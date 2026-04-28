import requests
import time
import json

BASE_URL = "http://localhost:8085"
API_KEY = "TravelHubSecretKey2026"
INSTANCE_NAME = "TH_NEW_1"

headers = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

def test_evolution():
    print(f"--- Iniciando Diagnóstico de Evolution API ({INSTANCE_NAME}) ---")
    
    # 1. Limpieza
    print(f"1. Cerrando sesión y eliminando instancia {INSTANCE_NAME}...")
    try:
        r1 = requests.delete(f"{BASE_URL}/instance/logout/{INSTANCE_NAME}", headers=headers, timeout=10)
        print(f"   Logout response: {r1.status_code} - {r1.text}")
        r2 = requests.delete(f"{BASE_URL}/instance/delete/{INSTANCE_NAME}", headers=headers, timeout=10)
        print(f"   Delete response: {r2.status_code} - {r2.text}")
    except Exception as e:
        print(f"   (Nota: Error en limpieza: {e})")

    # 1.5 Listar instancias
    print("1.5 Listando instancias existentes...")
    list_resp = requests.get(f"{BASE_URL}/instance/fetchInstances", headers=headers, timeout=10)
    print(f"    Instancias: {list_resp.text}")

    # 2. Creación
    print(f"2. Creando instancia {INSTANCE_NAME}...")
    payload = {
        "instanceName": INSTANCE_NAME,
        "token": API_KEY,
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS"
    }
    
    create_resp = requests.post(f"{BASE_URL}/instance/create", json=payload, headers=headers, timeout=15)
    print(f"   Status Create: {create_resp.status_code}")
    print(f"   Response Create: {create_resp.text}")

    # 3. Pausa crítica
    print("3. Pausa de 5 segundos para inicialización de llaves criptográficas...")
    time.sleep(5)

    # 4. Obtención de QR
    print(f"4. Solicitando QR de conexión para {INSTANCE_NAME}...")
    try:
        connect_resp = requests.get(f"{BASE_URL}/instance/connect/{INSTANCE_NAME}", headers=headers, timeout=15)
        print("\n--- RESPUESTA CRUDA DE EVOLUTION API ---")
        print(json.dumps(connect_resp.json(), indent=2))
        print("----------------------------------------\n")
    except Exception as e:
        print(f"❌ Error al conectar: {e}")
        if 'connect_resp' in locals():
            print(f"Status Code: {connect_resp.status_code}")
            print(f"Raw Body: {connect_resp.text}")

if __name__ == "__main__":
    test_evolution()

import requests
import time
import json

BASE_URL = "http://localhost:8085"
API_KEY = "TravelHubSecretKey2026"
# Usamos un nombre fresco para evitar el conflicto de base de datos
INSTANCE_NAME = "TH_DIAG_1"

headers = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

def test_evolution():
    print(f"--- Diagnóstico de Emergencia ({INSTANCE_NAME}) ---")
    
    # 1. Limpieza preventiva
    requests.delete(f"{BASE_URL}/instance/logout/{INSTANCE_NAME}", headers=headers, timeout=5)
    requests.delete(f"{BASE_URL}/instance/delete/{INSTANCE_NAME}", headers=headers, timeout=5)

    # 2. Creación
    print(f"1. Creando instancia fresca: {INSTANCE_NAME}...")
    payload = {
        "instanceName": INSTANCE_NAME,
        "token": API_KEY,
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS"
    }
    
    create_resp = requests.post(f"{BASE_URL}/instance/create", json=payload, headers=headers, timeout=15)
    print(f"   Status: {create_resp.status_code}")
    
    # 3. Pausa obligatoria
    print("2. Pausa de 5 segundos (Procesamiento de llaves)...")
    time.sleep(5)

    # 4. Obtención de QR
    print(f"3. Solicitando QR para {INSTANCE_NAME}...")
    try:
        connect_resp = requests.get(f"{BASE_URL}/instance/connect/{INSTANCE_NAME}", headers=headers, timeout=15)
        print("\n--- RESPUESTA CRUDA DE EVOLUTION API ---")
        print(json.dumps(connect_resp.json(), indent=2))
        print("----------------------------------------\n")
    except Exception as e:
        print(f"❌ Falló la conexión: {e}")

if __name__ == "__main__":
    test_evolution()

import requests
import json

# Configuración
BASE_URL = "http://localhost:8000/api"
USERNAME = "Armando3105"
PASSWORD = "Linkeo1331*"

def main():
    # 1. Obtener token
    login_data = {"username": USERNAME, "password": PASSWORD}
    response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
    token = response.json()["token"]
    headers = {"Authorization": f"Token {token}"}
    
    # 2. Crear venta mínima
    venta_data = {
        "cliente": 6,  # ID del cliente que sabemos que existe
        "moneda": 4,   # ID de la moneda que sabemos que existe
        "descripcion_general": "Venta de prueba",
        "items_venta": [
            {
                "producto_servicio": 2,  # ID del producto que sabemos que existe
                "precio_unitario_venta": 100.00,
                "cantidad": 1,
                "descripcion_personalizada": "Item de prueba"
            }
        ]
    }
    
    print("Creando venta...")
    print(json.dumps(venta_data, indent=2))
    
    try:
        response = requests.post(f"{BASE_URL}/ventas/", headers=headers, json=venta_data)
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 201:
            venta = response.json()
            print("¡VENTA CREADA EXITOSAMENTE!")
            print(f"ID: {venta['id_venta']}")
            print(f"Localizador: {venta['localizador']}")
            print(f"Total: {venta['total_venta']}")
        else:
            print("ERROR:")
            # Intentar mostrar solo los primeros 500 caracteres para evitar problemas de encoding
            error_text = response.text[:500] if len(response.text) > 500 else response.text
            print(error_text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
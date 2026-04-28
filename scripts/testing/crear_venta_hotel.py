import requests
import json
from datetime import datetime, timedelta

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
    
    # 2. Crear venta de hotel completa
    check_in = datetime.now() + timedelta(days=30)
    check_out = check_in + timedelta(days=3)
    
    venta_data = {
        "cliente": 6,
        "moneda": 4,
        "descripcion_general": "Reserva Hotel Marriott Caracas",
        "tipo_venta": "B2C",
        "canal_origen": "WEB",
        "items_venta": [
            {
                "producto_servicio": 2,
                "precio_unitario_venta": 450.00,
                "cantidad": 1,
                "descripcion_personalizada": "Hotel Marriott - Habitación Doble Superior",
                "fecha_inicio_servicio": check_in.isoformat(),
                "fecha_fin_servicio": check_out.isoformat(),
                "proveedor_servicio": 1,
                "alojamiento_details": {
                    "nombre_establecimiento": "Hotel Marriott Caracas",
                    "check_in": check_in.strftime("%Y-%m-%d"),
                    "check_out": check_out.strftime("%Y-%m-%d"),
                    "regimen_alimentacion": "Todo Incluido",
                    "habitaciones": 1,
                    "ciudad": 1,
                    "proveedor": 1,
                    "notas": "Habitación con vista al mar - Cliente VIP"
                }
            }
        ]
    }
    
    print("Creando venta de hotel...")
    print(json.dumps(venta_data, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(f"{BASE_URL}/ventas/", headers=headers, json=venta_data)
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 201:
            venta = response.json()
            print("¡VENTA DE HOTEL CREADA EXITOSAMENTE!")
            print(f"ID: {venta['id_venta']}")
            print(f"Localizador: {venta['localizador']}")
            print(f"Total: {venta['total_venta']}")
            print(f"Cliente: {venta.get('cliente_detalle', {}).get('get_nombre_completo', 'N/A')}")
            print(f"Alojamientos: {len(venta.get('alojamientos', []))}")
        else:
            print("ERROR:")
            print(response.text[:500])
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
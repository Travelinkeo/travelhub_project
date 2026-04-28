import requests
import json

# Configuración
BASE_URL = "http://localhost:8000/api"
USERNAME = "Armando3105"
PASSWORD = "Linkeo1331*"

def main():
    print("=== DIAGNÓSTICO API TRAVELHUB ===\n")
    
    # 1. Obtener token
    print("1. Obteniendo token...")
    login_data = {"username": USERNAME, "password": PASSWORD}
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
        print(f"   Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   Error: {response.text}")
            return
            
        token = response.json()["token"]
        print(f"   Token obtenido: {token[:20]}...")
        
    except Exception as e:
        print(f"   Error: {e}")
        return
    
    headers = {"Authorization": f"Token {token}"}
    
    # 2. Verificar catálogos básicos
    print("\n2. Verificando catálogos...")
    
    catalogos = {
        "clientes": f"{BASE_URL}/clientes/",
        "monedas": f"{BASE_URL}/monedas/", 
        "productos": f"{BASE_URL}/productos-servicio/",
        "ciudades": f"{BASE_URL}/ciudades/",
        "proveedores": f"{BASE_URL}/proveedores/"
    }
    
    datos_disponibles = {}
    
    for nombre, url in catalogos.items():
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "results" in data:
                    items = data["results"]
                else:
                    items = data
                count = len(items) if isinstance(items, list) else 1
                print(f"   {nombre}: {count} registros")
                datos_disponibles[nombre] = items
            else:
                print(f"   {nombre}: ERROR {response.status_code}")
        except Exception as e:
            print(f"   {nombre}: ERROR {e}")
    
    # 3. Intentar crear venta simple
    print("\n3. Creando venta de prueba...")
    
    if not datos_disponibles.get("clientes"):
        print("   ERROR: No hay clientes disponibles")
        return
        
    if not datos_disponibles.get("monedas"):
        print("   ERROR: No hay monedas disponibles")
        return
        
    if not datos_disponibles.get("productos"):
        print("   ERROR: No hay productos disponibles")
        return
    
    # Usar el primer registro de cada catálogo
    cliente_id = datos_disponibles["clientes"][0]["id_cliente"]
    moneda_id = datos_disponibles["monedas"][0]["id_moneda"]
    producto_id = datos_disponibles["productos"][0]["id_producto_servicio"]
    
    venta_data = {
        "cliente": cliente_id,
        "moneda": moneda_id,
        "items_venta": [
            {
                "producto_servicio": producto_id,
                "precio_unitario_venta": 100.00
            }
        ]
    }
    
    print(f"   Datos: Cliente={cliente_id}, Moneda={moneda_id}, Producto={producto_id}")
    
    try:
        response = requests.post(f"{BASE_URL}/ventas/", headers=headers, json=venta_data)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 201:
            venta = response.json()
            print(f"   ¡ÉXITO! Venta creada: ID={venta['id_venta']}, Localizador={venta['localizador']}")
        else:
            print(f"   ERROR: {response.text}")
            
    except Exception as e:
        print(f"   ERROR: {e}")
    
    print("\n=== FIN DIAGNÓSTICO ===")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Script de prueba para verificar la creación de ventas de hotel
Ejecutar desde el directorio del proyecto: python test_hotel_api.py
"""

import requests
import json
from datetime import datetime, timedelta

# Configuración
BASE_URL = "http://localhost:8000/api"
USERNAME = "Armando3105"
PASSWORD = "Linkeo1331*"

def obtener_token():
    """Obtiene el token de autenticación"""
    url = f"{BASE_URL}/auth/login/"
    data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        print(f"Login response status: {response.status_code}")
        if response.status_code == 200:
            return response.json()["token"]
        else:
            print(f"Error obteniendo token: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión: {e}")
        return None

def obtener_catalogos(token):
    """Obtiene los catálogos necesarios (clientes, monedas, productos, ciudades, proveedores)"""
    headers = {"Authorization": f"Token {token}"}
    
    catalogos = {}
    
    # Obtener clientes
    response = requests.get(f"{BASE_URL}/clientes/", headers=headers)
    if response.status_code == 200:
        clientes = response.json()
        catalogos["clientes"] = clientes["results"] if "results" in clientes else clientes
        print(f"Clientes disponibles: {len(catalogos['clientes'])}")
    
    # Obtener monedas
    response = requests.get(f"{BASE_URL}/monedas/", headers=headers)
    if response.status_code == 200:
        monedas = response.json()
        catalogos["monedas"] = monedas["results"] if "results" in monedas else monedas
        print(f"Monedas disponibles: {len(catalogos['monedas'])}")
    
    # Obtener productos/servicios
    response = requests.get(f"{BASE_URL}/productos-servicio/", headers=headers)
    if response.status_code == 200:
        productos = response.json()
        catalogos["productos"] = productos["results"] if "results" in productos else productos
        print(f"Productos disponibles: {len(catalogos['productos'])}")
    
    # Obtener ciudades
    response = requests.get(f"{BASE_URL}/ciudades/", headers=headers)
    if response.status_code == 200:
        ciudades = response.json()
        catalogos["ciudades"] = ciudades["results"] if "results" in ciudades else ciudades
        print(f"Ciudades disponibles: {len(catalogos['ciudades'])}")
    
    # Obtener proveedores
    response = requests.get(f"{BASE_URL}/proveedores/", headers=headers)
    if response.status_code == 200:
        proveedores = response.json()
        catalogos["proveedores"] = proveedores["results"] if "results" in proveedores else proveedores
        print(f"Proveedores disponibles: {len(catalogos['proveedores'])}")
    
    return catalogos

def crear_venta_hotel(token, catalogos):
    """Crea una venta de hotel de prueba"""
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }
    
    # Buscar IDs necesarios
    cliente_id = catalogos["clientes"][0]["id_cliente"] if catalogos["clientes"] else 1
    moneda_id = catalogos["monedas"][0]["id_moneda"] if catalogos["monedas"] else 1
    
    # Buscar producto de hotel
    producto_hotel = None
    for producto in catalogos["productos"]:
        if "hotel" in producto.get("nombre", "").lower() or producto.get("tipo_producto") == "HOT":
            producto_hotel = producto
            break
    
    if not producto_hotel:
        print("No se encontró un producto de tipo hotel. Usando el primer producto disponible.")
        producto_hotel = catalogos["productos"][0] if catalogos["productos"] else {"id_producto_servicio": 1}
    
    ciudad_id = catalogos["ciudades"][0]["id_ciudad"] if catalogos["ciudades"] else 1
    proveedor_id = catalogos["proveedores"][0]["id_proveedor"] if catalogos["proveedores"] else 1
    
    # Fechas para la reserva
    check_in = datetime.now() + timedelta(days=30)
    check_out = check_in + timedelta(days=3)
    
    # Estructura de la venta
    venta_data = {
        "cliente": cliente_id,
        "moneda": moneda_id,
        "tipo_venta": "B2C",
        "canal_origen": "WEB",
        "descripcion_general": "Reserva de hotel - Prueba API",
        "subtotal": 450.00,
        "impuestos": 45.00,
        "notas": "Venta de prueba creada desde script de testing",
        "items_venta": [
            {
                "producto_servicio": producto_hotel["id_producto_servicio"],
                "descripcion_personalizada": "Hotel Marriott - Habitación Doble Superior",
                "cantidad": 1,
                "precio_unitario_venta": 450.00,
                "fecha_inicio_servicio": check_in.isoformat(),
                "fecha_fin_servicio": check_out.isoformat(),
                "proveedor_servicio": proveedor_id,
                "costo_neto_proveedor": 350.00,
                "fee_proveedor": 25.00,
                "comision_agencia_monto": 50.00,
                "fee_agencia_interno": 25.00,
                "notas_item": "Habitación con vista al mar - Prueba API",
                "alojamiento_details": {
                    "nombre_establecimiento": "Hotel Marriott Caracas",
                    "check_in": check_in.strftime("%Y-%m-%d"),
                    "check_out": check_out.strftime("%Y-%m-%d"),
                    "regimen_alimentacion": "Todo Incluido",
                    "habitaciones": 1,
                    "ciudad": ciudad_id,
                    "proveedor": proveedor_id,
                    "notas": "Habitación con vista al mar solicitada - Prueba API"
                }
            }
        ]
    }
    
    print("\n=== CREANDO VENTA DE HOTEL ===")
    print(f"Datos a enviar:")
    print(json.dumps(venta_data, indent=2, ensure_ascii=False))
    
    response = requests.post(f"{BASE_URL}/ventas/", headers=headers, json=venta_data)
    
    print(f"\nRespuesta del servidor: {response.status_code}")
    
    if response.status_code == 201:
        venta_creada = response.json()
        print("[OK] VENTA CREADA EXITOSAMENTE!")
        print(f"ID Venta: {venta_creada.get('id_venta')}")
        print(f"Localizador: {venta_creada.get('localizador')}")
        print(f"Total: {venta_creada.get('total_venta')}")
        return venta_creada
    else:
        print("[ERROR] ERROR AL CREAR LA VENTA:")
        try:
            error_data = response.json()
            print(json.dumps(error_data, indent=2, ensure_ascii=False))
        except:
            print(response.text)
        return None

def main():
    print("=== SCRIPT DE PRUEBA - VENTA DE HOTEL ===")
    
    # 1. Obtener token
    print("\n1. Obteniendo token de autenticación...")
    token = obtener_token()
    if not token:
        print("[ERROR] No se pudo obtener el token. Verifica las credenciales.")
        return
    
    print("[OK] Token obtenido correctamente")
    
    # 2. Obtener catálogos
    print("\n2. Obteniendo catálogos...")
    catalogos = obtener_catalogos(token)
    
    # 3. Crear venta de hotel
    print("\n3. Creando venta de hotel...")
    venta = crear_venta_hotel(token, catalogos)
    
    if venta:
        print(f"\n[EXITO] PROCESO COMPLETADO EXITOSAMENTE!")
        print(f"Puedes ver la venta en: http://localhost:8000/admin/core/venta/{venta['id_venta']}/change/")
    else:
        print("\n[FALLO] PROCESO FALLO. Revisa los errores arriba.")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Script para probar todos los endpoints que usa el frontend
"""

import requests

BASE_URL = "http://127.0.0.1:8000/api"

def test_endpoint(endpoint, description):
    try:
        response = requests.get(f"{BASE_URL}{endpoint}")
        status = "[OK]" if response.status_code == 200 else "[ERROR]"
        print(f"{status} {description}: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and 'results' in data:
                count = len(data['results'])
            elif isinstance(data, list):
                count = len(data)
            else:
                count = 1
            print(f"   Registros: {count}")
        else:
            print(f"   Error: {response.text[:100]}")
    except Exception as e:
        print(f"[ERROR] {description}: Error de conexión - {e}")

def main():
    print("=== PRUEBA DE ENDPOINTS DEL FRONTEND ===\n")
    
    endpoints = [
        ("/clientes/", "Clientes"),
        ("/clientes/?search=armando", "Búsqueda de clientes"),
        ("/monedas/", "Monedas"),
        ("/monedas/?search=us", "Búsqueda de monedas"),
        ("/productos-servicio/", "Productos/Servicios"),
        ("/productos-servicio/?search=hotel", "Búsqueda de productos"),
        ("/ciudades/", "Ciudades"),
        ("/ciudades/?search=cara", "Búsqueda de ciudades"),
        ("/proveedores/", "Proveedores"),
        ("/proveedores/?search=", "Búsqueda de proveedores (vacía)"),
        ("/proveedores/?search=bt", "Búsqueda de proveedores"),
    ]
    
    for endpoint, description in endpoints:
        test_endpoint(endpoint, description)
        print()
    
    print("=== RESUMEN ===")
    print("Si todos los endpoints muestran [OK], el frontend debería funcionar correctamente.")
    print("Si hay [ERROR], revisa los errores mostrados arriba.")

if __name__ == "__main__":
    main()
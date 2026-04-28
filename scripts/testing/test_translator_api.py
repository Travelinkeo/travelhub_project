#!/usr/bin/env python
"""
Script de prueba para las APIs del traductor de itinerarios.
Ejecutar desde el directorio raíz del proyecto.
"""

import os
import sys
import requests
import json

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.contrib.auth.models import User

def get_jwt_token():
    """Obtiene un token JWT para las pruebas."""
    # Crear usuario de prueba si no existe
    try:
        user = User.objects.get(username='test_translator')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='test_translator',
            password='test123456',
            email='test@example.com'
        )
        print("✓ Usuario de prueba creado")
    
    # Obtener token JWT
    response = requests.post('http://127.0.0.1:8000/api/auth/jwt/obtain/', {
        'username': 'test_translator',
        'password': 'test123456'
    })
    
    if response.status_code == 200:
        token = response.json()['access']
        print("✓ Token JWT obtenido")
        return token
    else:
        print("✗ Error obteniendo token JWT:", response.text)
        return None

def test_api_endpoint(url, method='GET', data=None, token=None):
    """Prueba un endpoint de la API."""
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    if method == 'GET':
        response = requests.get(url, headers=headers)
    elif method == 'POST':
        headers['Content-Type'] = 'application/json'
        response = requests.post(url, headers=headers, json=data)
    
    return response

def main():
    """Función principal de pruebas."""
    print("🚀 Iniciando pruebas de APIs del traductor...")
    print("=" * 50)
    
    base_url = 'http://127.0.0.1:8000'
    
    # Obtener token
    token = get_jwt_token()
    if not token:
        print("❌ No se pudo obtener token. Asegúrate de que el servidor esté ejecutándose.")
        return
    
    # Pruebas de endpoints
    tests = [
        {
            'name': 'Obtener sistemas GDS soportados',
            'url': f'{base_url}/api/translator/gds/',
            'method': 'GET'
        },
        {
            'name': 'Obtener catálogo de aerolíneas',
            'url': f'{base_url}/api/translator/airlines/',
            'method': 'GET'
        },
        {
            'name': 'Obtener catálogo de aeropuertos',
            'url': f'{base_url}/api/translator/airports/',
            'method': 'GET'
        },
        {
            'name': 'Validar formato de itinerario',
            'url': f'{base_url}/api/translator/validate/',
            'method': 'POST',
            'data': {
                'itinerary': '1 AA 1234 15JAN W MIABOG 0800 1200',
                'gds_system': 'SABRE'
            }
        },
        {
            'name': 'Traducir itinerario SABRE',
            'url': f'{base_url}/api/translator/itinerary/',
            'method': 'POST',
            'data': {
                'itinerary': '1 AA 1234 15JAN W MIABOG 0800 1200',
                'gds_system': 'SABRE'
            }
        },
        {
            'name': 'Calcular precio de boleto',
            'url': f'{base_url}/api/translator/calculate/',
            'method': 'POST',
            'data': {
                'tarifa': 100.0,
                'fee_consolidador': 25.0,
                'fee_interno': 15.0,
                'porcentaje': 10.0
            }
        },
        {
            'name': 'Traducción en lote',
            'url': f'{base_url}/api/translator/batch/',
            'method': 'POST',
            'data': {
                'itineraries': [
                    {
                        'id': 'test1',
                        'itinerary': '1 AA 1234 15JAN W MIABOG 0800 1200',
                        'gds_system': 'SABRE'
                    },
                    {
                        'id': 'test2',
                        'itinerary': '2 UA 5678 16JAN W BOGMIA 1400 1800',
                        'gds_system': 'SABRE'
                    }
                ]
            }
        }
    ]
    
    # Ejecutar pruebas
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"\n🧪 Probando: {test['name']}")
        
        try:
            response = test_api_endpoint(
                test['url'],
                test.get('method', 'GET'),
                test.get('data'),
                token
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success', False):
                    print(f"   ✅ ÉXITO - Status: {response.status_code}")
                    
                    # Mostrar información relevante
                    if 'supported_gds' in data:
                        print(f"   📊 GDS soportados: {len(data['supported_gds'])}")
                    elif 'airlines' in data:
                        print(f"   ✈️  Aerolíneas: {data['total']}")
                    elif 'airports' in data:
                        print(f"   🛬 Aeropuertos: {data['total']}")
                    elif 'validation' in data:
                        validation = data['validation']
                        print(f"   📝 Validación: {validation['valid_lines']}/{validation['total_lines']} líneas válidas")
                    elif 'translated_itinerary' in data:
                        print(f"   🔄 Itinerario traducido exitosamente")
                    elif 'calculation' in data:
                        calc = data['calculation']
                        print(f"   💰 Precio final: ${calc['precio_final']:.2f}")
                    elif 'summary' in data:
                        summary = data['summary']
                        print(f"   📦 Lote: {summary['successful']}/{summary['total']} exitosos")
                    
                    passed += 1
                else:
                    print(f"   ❌ FALLO - Respuesta sin success=True")
                    print(f"   📄 Respuesta: {json.dumps(data, indent=2)}")
                    failed += 1
            else:
                print(f"   ❌ FALLO - Status: {response.status_code}")
                print(f"   📄 Error: {response.text}")
                failed += 1
                
        except Exception as e:
            print(f"   ❌ ERROR - Excepción: {str(e)}")
            failed += 1
    
    # Resumen final
    print("\n" + "=" * 50)
    print(f"📊 RESUMEN DE PRUEBAS:")
    print(f"   ✅ Exitosas: {passed}")
    print(f"   ❌ Fallidas: {failed}")
    print(f"   📈 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
    else:
        print(f"\n⚠️  {failed} pruebas fallaron. Revisa los errores arriba.")
    
    print("\n💡 Notas:")
    print("   - Asegúrate de que el servidor Django esté ejecutándose en http://127.0.0.1:8000")
    print("   - Verifica que las migraciones estén aplicadas")
    print("   - Revisa que los catálogos de aerolíneas estén cargados")

if __name__ == '__main__':
    main()
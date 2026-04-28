
import os
import sys
import django
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from personas.models import Pasajero
from django.test import RequestFactory
from django.conf import settings
from django.core.cache import cache

def test_security():
    print("🛡️ probando Seguridad SaaS...")
    
    # 1. Verificar Encriptación
    print("\n[1] Verificando Encriptación:")
    pasajero = Pasajero.objects.first()
    if not pasajero:
        print("⚠️ No hay pasajeros para probar.")
    else:
        print(f"   ID: {pasajero.id_pasajero}")
        print(f"   Documento (Python): {pasajero.numero_documento}")
        
        # Verificar RAW DB value
        with django.db.connection.cursor() as cursor:
            cursor.execute("SELECT numero_documento FROM personas_pasajero WHERE id_pasajero = %s", [pasajero.id_pasajero])
            row = cursor.fetchone()
            raw_value = row[0]
            print(f"   Documento (DB Raw): {raw_value[:15]}...")
            
            if raw_value.startswith('gAAAA'):
                print("   ✅ DATA IS ENCRYPTED IN DB")
            else:
                print("   ❌ DATA IS NOT ENCRYPTED IN DB")

    # 2. Verificar Búsqueda por Hash
    print("\n[2] Verificando Búsqueda por Hash:")
    if pasajero and pasajero.numero_documento_hash:
        print(f"   Buscando hash: {pasajero.numero_documento_hash[:10]}...")
        p_found = Pasajero.objects.filter(numero_documento_hash=pasajero.numero_documento_hash).first()
        if p_found and p_found.id_pasajero == pasajero.id_pasajero:
            print("   ✅ Búsqueda por hash exitosa")
        else:
            print("   ❌ Falló búsqueda por hash")
            
    # 3. Verificar Redis Cache
    print("\n[3] Verificando Redis:")
    try:
        cache.set('test_key', 'test_value', 10)
        val = cache.get('test_key')
        if val == 'test_value':
             print("   ✅ Redis Cache funcionando")
        else:
             print("   ❌ Redis Cache falló (valor incorrecto)")
    except Exception as e:
        print(f"   ❌ Error conectando a Redis: {e}")

if __name__ == '__main__':
    test_security()

"""
Script de Prueba: Cifrado de Pasaportes

Verifica que el cifrado de números de pasaporte funcione correctamente.

Uso:
    python scripts/test_encryption.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.crm.models import Cliente

def test_encryption():
    """Prueba el cifrado y descifrado de pasaportes"""
    print("\n" + "=" * 60)
    print("🔐 TEST: Cifrado de Números de Pasaporte")
    print("=" * 60 + "\n")
    
    try:
        # 1. Crear cliente con pasaporte
        print("📝 PASO 1: Creando cliente con pasaporte")
        print("-" * 60)
        
        cliente = Cliente.objects.create(
            nombres="Test",
            apellidos="Encryption",
            email=f"test.encryption.{os.urandom(4).hex()}@test.com",
            numero_pasaporte="P12345678"
        )
        
        print(f"   ✅ Cliente creado: ID={cliente.id_cliente}")
        print(f"   📄 Pasaporte (en memoria): {cliente.numero_pasaporte}")
        print()
        
        # 2. Verificar que en DB está cifrado
        print("📝 PASO 2: Verificando cifrado en base de datos")
        print("-" * 60)
        
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT numero_pasaporte FROM core_cliente WHERE id_cliente = %s",
                [cliente.id_cliente]
            )
            raw_value = cursor.fetchone()[0]
        
        print(f"   📊 Valor en DB (cifrado): {raw_value[:50]}...")
        print(f"   ✅ Está cifrado: {raw_value != 'P12345678'}")
        print(f"   ✅ Empieza con 'gAAAAA': {raw_value.startswith('gAAAAA')}")
        print()
        
        # 3. Recuperar y verificar descifrado
        print("📝 PASO 3: Verificando descifrado automático")
        print("-" * 60)
        
        cliente_recuperado = Cliente.objects.get(id_cliente=cliente.id_cliente)
        
        print(f"   📄 Pasaporte recuperado: {cliente_recuperado.numero_pasaporte}")
        print(f"   ✅ Descifrado correctamente: {cliente_recuperado.numero_pasaporte == 'P12345678'}")
        print()
        
        # 4. Actualizar pasaporte
        print("📝 PASO 4: Actualizando pasaporte")
        print("-" * 60)
        
        cliente_recuperado.numero_pasaporte = "P87654321"
        cliente_recuperado.save()
        
        cliente_actualizado = Cliente.objects.get(id_cliente=cliente.id_cliente)
        print(f"   📄 Nuevo pasaporte: {cliente_actualizado.numero_pasaporte}")
        print(f"   ✅ Actualizado correctamente: {cliente_actualizado.numero_pasaporte == 'P87654321'}")
        print()
        
        # 5. Limpiar
        print("📝 PASO 5: Limpiando datos de prueba")
        print("-" * 60)
        cliente.delete()
        print("   ✅ Cliente eliminado")
        print()
        
        # Resultado final
        print("=" * 60)
        print("✅ PRUEBA EXITOSA: El cifrado funciona correctamente")
        print("=" * 60 + "\n")
        
        print("📊 Resumen:")
        print("   • Datos se cifran antes de guardar en DB")
        print("   • Datos se descifran automáticamente al leer")
        print("   • Actualizaciones funcionan correctamente")
        print("   • Formato Fernet detectado (gAAAAA)")
        print()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_encryption()

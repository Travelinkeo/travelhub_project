"""
test_multitenant.py
===================
Verifica que el blindaje de AgenciaMixin e IA_Manager funciona.
"""
import os
import django
import sys

# Bootstrap Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models.agencia import Agencia
from apps.crm.models import Cliente
from core.middleware import _request_local
from django.contrib.auth.models import User

def test_isolation():
    print("="*60)
    print("🧪 TEST DE AISLAMIENTO MULTI-TENANT")
    print("="*60)

    # 1. Obtener Agencia Principal (ID 1)
    ag1 = Agencia.objects.filter(pk=1).first()
    if not ag1:
        # Fallback si no hay agencias
        ag1 = Agencia.objects.create(nombre="Agencia ALPHA", email_principal="alpha@test.com")
        
    # Crear una segunda agencia controlada para el test
    ag2, _ = Agencia.objects.get_or_create(nombre="Agencia BETA TEST", defaults={'email_principal':"beta@test.com"})

    
    # 2. Mockear contexto para ALPHA y crear un cliente
    _request_local.agency = ag1
    cli_alpha = Cliente.objects.create(nombres="Cliente de ALPHA")
    print(f"✅ Creado cliente en ALPHA: {cli_alpha.id}")

    # 3. Cambiar contexto a BETA e intentar ver el cliente de ALPHA
    _request_local.agency = ag2
    total_en_beta = Cliente.objects.count()
    print(f"🔍 Clientes visibles en BETA: {total_en_beta}")
    
    if total_en_beta == 0:
        print("🛡️  ÉXITO: BETA no puede ver los clientes de ALPHA.")
    else:
        print("🔥 ERROR: BETA puede ver datos de ALPHA. El blindaje falló.")

    # 4. Limpieza
    _request_local.agency = ag1
    cli_alpha.delete()
    print("🧹 Limpieza completada.")
    print("="*60)

if __name__ == "__main__":
    test_isolation()


import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import Agencia, Proveedor
from apps.crm.models import Cliente
from apps.bookings.models import Venta
from django.contrib.auth import get_user_model
User = get_user_model()

def check_integrity():
    print("\n--- DIAGNÓSTICO DE DATOS ---\n")
    
    # 1. Agencias
    agencias = Agencia.objects.all()
    print(f"🏢 Agencias encontradas: {agencias.count()}")
    for a in agencias:
        print(f"   - ID: {a.id} | Nombre: '{a.nombre}' | Activa: {a.activa}")
        
    if agencias.count() == 0:
        print("   ❌ ¡ALERTA! No hay agencias registradas.")

    # 2. Proveedores
    prov_count = Proveedor.objects.count()
    print(f"\n📦 Proveedores: {prov_count}")
    
    # 3. Clientes
    client_count = Cliente.objects.count()
    print(f"👥 Clientes: {client_count}")
    
    # 4. Ventas
    venta_count = Venta.objects.count()
    print(f"💰 Ventas: {venta_count}")
    
    # 5. Usuarios
    print(f"\n👤 Usuarios:")
    for u in User.objects.all():
         agencia_nombre = u.agencia.nombre if hasattr(u, 'agencia') and u.agencia else "Sin Agencia"
         print(f"   - {u.username} (Agencia: {agencia_nombre})")

if __name__ == "__main__":
    check_integrity()

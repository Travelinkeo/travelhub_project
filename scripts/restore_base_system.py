
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import Agencia, Proveedor
from django.contrib.auth import get_user_model
User = get_user_model()

def restore_system():
    print("--- RESTAURACIÓN DE EMERGENCIA ---")
    
    # 1. Recuperar Agencia Principal
    agencia, created = Agencia.objects.get_or_create(
        nombre="Travelinkeo",
        defaults={
            'activa': True,
            'direccion': 'Caracas, Venezuela',
            'email_contacto': 'admin@travelinkeo.com'
        }
    )
    if created:
        print("✅ Agencia 'Travelinkeo' recreada.")
    else:
        print("ℹ️ Agencia 'Travelinkeo' ya existía.")
        
    # 2. Asignar Agencia al Admin
    u = User.objects.filter(username='admin').first()
    if u:
        u.agencia = agencia
        u.save()
        print(f"✅ Usuario 'admin' vinculado a Travelinkeo.")
        
    # 3. Crear Proveedores Básicos (TravelLink, KIU, Sabre) si no existen
    proveedores = ['TravelLink', 'KIU', 'Sabre', 'Amadeus']
    for p_name in proveedores:
        Proveedor.objects.get_or_create(nombre_empresa=p_name, defaults={'activo': True, 'agencia': agencia})
    print(f"✅ Proveedores básicos restaurados.")

if __name__ == "__main__":
    restore_system()

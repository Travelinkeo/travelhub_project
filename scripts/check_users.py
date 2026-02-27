
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

def check_users():
    print("--- Usuarios en Base de Datos ---")
    users = User.objects.all()
    if not users.exists():
        print("⚠️ ALERTA: No existen usuarios en la base de datos.")
    
    for u in users:
        print(f"ID: {u.id} | Usuario: {u.username} | Email: {u.email} | Activo: {u.is_active} | Superuser: {u.is_superuser}")

if __name__ == "__main__":
    check_users()


import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

def reset_password():
    print("--- Restaurando Acceso ---")
    u = User.objects.filter(is_superuser=True).first()
    if u:
        u.set_password('travelhub2026')
        u.save()
        print(f"✅ Contraseña restablecida para el usuario: '{u.username}'")
        print(f"🔑 Nueva contraseña: travelhub2026")
    else:
        print("❌ No se encontró superusuario para restablecer.")

if __name__ == "__main__":
    reset_password()

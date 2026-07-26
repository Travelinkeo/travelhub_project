import os
import sys
from getpass import getpass

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()


def reset_password():
    """reset_password."""
    print("--- Restaurando Acceso ---")
    u = User.objects.filter(is_superuser=True).first()
    if u:
        new_password = getpass("Ingrese la nueva contraseña: ")
        confirm_password = getpass("Confirme la nueva contraseña: ")

        if new_password != confirm_password:
            print("Las contraseñas no coinciden.")
            return

        if len(new_password) < 8:
            print("La contraseña debe tener al menos 8 caracteres.")
            return

        u.set_password(new_password)
        u.save()
        print(f"Contrasena restablecida para el usuario: '{u.username}'")
    else:
        print("No se encontro superusuario para restablecer.")


if __name__ == "__main__":
    reset_password()

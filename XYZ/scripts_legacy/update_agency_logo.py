import os
import sys
from django.core.files import File
from django.conf import settings
from django.contrib.auth import get_user_model
from core.models import Agencia

# Path provided by user
USER_LOGO_PATH = r"C:\Users\ARMANDO\travelhub_project\static\images\Logo Blanco.png"

def update_logo():
    try:
        User = get_user_model()
        try:
            user = User.objects.get(username='agent')
        except User.DoesNotExist:
            print("User 'agent' not found.")
            return

        agencia = user.agencia
        if not agencia:
            print(f"User '{user.username}' has no agency assigned.")
            # Try to find 'Agencia Test'
            agencia = Agencia.objects.filter(nombre='Agencia Test').first()
            if agencia:
                print(f"Found 'Agencia Test', assigning to user '{user.username}'")
                user.agencia = agencia
                user.save()
            else:
                print("No agency found to update.")
                return

        print(f"Updating logo for agency: {agencia.nombre} (ID: {agencia.id})")

        if os.path.exists(USER_LOGO_PATH):
            print(f"Found logo file at {USER_LOGO_PATH}")
            # Create media directory if it doesn't exist
            media_dir = os.path.join(settings.MEDIA_ROOT, 'agencias', 'logos')
            os.makedirs(media_dir, exist_ok=True)
            
            # Copy file to a temporary location or open directly
            with open(USER_LOGO_PATH, 'rb') as f:
                agencia.logo.save('logo_blanco.png', File(f), save=True)
            
            print(f"SUCCESS: Updated logo for agency '{agencia.nombre}'")
            print(f"New logo URL: {agencia.logo.url}")
        else:
            print(f"ERROR: Logo file not found at {USER_LOGO_PATH}")

    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_logo()

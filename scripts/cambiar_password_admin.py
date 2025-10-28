#!/usr/bin/env python
"""Script para cambiar el password del usuario admin de forma segura."""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.contrib.auth.models import User
from getpass import getpass

def cambiar_password_admin():
    try:
        admin = User.objects.get(username='admin')
    except User.DoesNotExist:
        print("❌ Usuario 'admin' no existe")
        return
    
    print("🔐 Cambiar password del usuario 'admin'")
    print("=" * 50)
    
    nueva_password = getpass("Nueva password: ")
    confirmar_password = getpass("Confirmar password: ")
    
    if nueva_password != confirmar_password:
        print("❌ Las passwords no coinciden")
        return
    
    if len(nueva_password) < 8:
        print("❌ La password debe tener al menos 8 caracteres")
        return
    
    admin.set_password(nueva_password)
    admin.save()
    
    print("✅ Password cambiado exitosamente")
    print("⚠️  IMPORTANTE: Guarda esta password en un lugar seguro")

if __name__ == '__main__':
    cambiar_password_admin()

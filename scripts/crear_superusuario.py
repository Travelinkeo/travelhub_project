#!/usr/bin/env python
"""Script para crear superusuario de forma segura."""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.contrib.auth.models import User
from getpass import getpass

def crear_superusuario():
    print("🔐 Crear Superusuario")
    print("=" * 50)
    
    username = input("Username: ").strip()
    if not username:
        print("❌ Username no puede estar vacío")
        return
    
    if User.objects.filter(username=username).exists():
        print(f"❌ Usuario '{username}' ya existe")
        return
    
    email = input("Email: ").strip()
    
    password = getpass("Password: ")
    confirmar = getpass("Confirmar password: ")
    
    if password != confirmar:
        print("❌ Las passwords no coinciden")
        return
    
    if len(password) < 8:
        print("❌ La password debe tener al menos 8 caracteres")
        return
    
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    
    print(f"✅ Superusuario '{username}' creado exitosamente")
    print("⚠️  IMPORTANTE: Guarda estas credenciales en un lugar seguro")

if __name__ == '__main__':
    crear_superusuario()

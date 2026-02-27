# restore_users.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Agencia, UsuarioAgencia

def restore():
    print("--- Iniciando Restauración de Usuarios ---")
    
    # 0. Asegurar que existe un Owner válido (usaremos admin o Armando si existe)
    admin_user = User.objects.filter(is_superuser=True).first()
    
    # 1. Recuperar o Crear Agencia Travelinkeo
    # Necesitamos un propietario por defecto si se crea de cero
    defaults_agencia = {
        "email_ventas": "viajes.travelinkeo@gmail.com",
        "telefono_principal": "+584126080861",
        "email_principal": "viajes.travelinkeo@gmail.com",
        "propietario": admin_user if admin_user else None 
    }
    
    # Si no hay propietario y no existe la agencia, fallaría. 
    # Pero como ya existe (check previo), el get no dará problemas.
    # Si no existiera, necesitamos crear el usuario primero.
    
    agencia_exists = Agencia.objects.filter(nombre="Travelinkeo").exists()
    
    # Crea usuarios primero
    usuarios_data = [
        {"username": "Armando3105", "email": "armando@travelinkeo.com", "is_staff": True, "is_superuser": True, "rol": "admin"},
        {"username": "Naidaly", "email": "naidaly@travelinkeo.com", "is_staff": True, "is_superuser": False, "rol": "gerente"},
    ]
    
    default_pass = "Travelhub2026!"
    users_objs = {}

    for u_data in usuarios_data:
        user, created = User.objects.get_or_create(
            username=u_data["username"],
            defaults={
                "email": u_data["email"],
                "is_staff": u_data["is_staff"],
                "is_superuser": u_data["is_superuser"]
            }
        )
        if created:
            user.set_password(default_pass)
            user.save()
            print(f"✅ Usuario '{u_data['username']}' restaurado. Password: {default_pass}")
        else:
            print(f"ℹ️ Usuario '{u_data['username']}' ya existe.")
            # Asegurar password si se desea (opcional, no lo haremos por seguridad para no resetear si ya lo cambiaron)
        
        users_objs[u_data["username"]] = user

    # Ahora sí la Agencia
    if not agencia_exists:
        # Usar Armando como propietario
        propietario = users_objs.get("Armando3105") or admin_user
        defaults_agencia["propietario"] = propietario
        agencia, created = Agencia.objects.get_or_create(
            nombre="Travelinkeo",
            defaults=defaults_agencia
        )
        if created:
             print("✅ Agencia 'Travelinkeo' creada.")
    else:
        agencia = Agencia.objects.get(nombre="Travelinkeo")
        print("ℹ️ Agencia 'Travelinkeo' ya existía.")

    # 3. Vincular Usuarios a Agencia usando UsuarioAgencia
    for u_data in usuarios_data:
        user = users_objs[u_data["username"]]
        ua, created = UsuarioAgencia.objects.get_or_create(
            usuario=user,
            agencia=agencia,
            defaults={'rol': u_data['rol']}
        )
        if created:
            print(f"✅ Usuario {user.username} vinculado a Travelinkeo como {u_data['rol']}.")
        else:
            print(f"ℹ️ Vínculo de {user.username} ya existía.")

    print("\n--- Restauración Completada ---")

if __name__ == '__main__':
    restore()

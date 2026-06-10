from django.contrib.auth import get_user_model

from core.models import Agencia, UsuarioAgencia

User = get_user_model()

# Crear usuarios administradores
users_data = [
    {"username": "Armando3105", "email": "armando@travelhub.cc"},
    {"username": "Naida1309", "email": "naida@travelhub.cc"},
]

for user_data in users_data:
    if not User.objects.filter(username=user_data["username"]).exists():
        user = User.objects.create_superuser(
            username=user_data["username"], email=user_data["email"], password="viaggio1"
        )
        print(f'✅ Usuario creado: {user_data["username"]}')
    else:
        user = User.objects.get(username=user_data["username"])
        user.set_password("viaggio1")
        user.save()
        print(f'🔄 Contraseña actualizada: {user_data["username"]}')

# Crear agencias
agencias_data = [
    {
        "nombre": "TravelHub",
        "nombre_comercial": "TravelHub Demo",
        "email_principal": "demo@travelhub.cc",
        "activa": True,
    },
    {
        "nombre": "Travelinkeo",
        "nombre_comercial": "Travelinkeo",
        "email_principal": "admin@travelinkeo.com",
        "activa": True,
    },
]

for agencia_data in agencias_data:
    if not Agencia.objects.filter(nombre=agencia_data["nombre"]).exists():
        agencia = Agencia.objects.create(**agencia_data)
        print(f'✅ Agencia creada: {agencia_data["nombre"]}')
    else:
        agencia = Agencia.objects.get(nombre=agencia_data["nombre"])
        print(f'🔄 Agencia existente: {agencia_data["nombre"]}')

# Asociar usuarios a agencias como administradores
for user in User.objects.filter(username__in=["Armando3105", "Naida1309"]):
    for agencia in Agencia.objects.all():
        if not UsuarioAgencia.objects.filter(usuario=user, agencia=agencia).exists():
            UsuarioAgencia.objects.create(usuario=user, agencia=agencia, rol="admin", activo=True)
            print(f"✅ {user.username} asociado a {agencia.nombre} como admin")

print("\n✨ Configuración completada exitosamente")
print("📋 Usuarios creados: Armando3105, Naida1309")
print("🏢 Agencias creadas: TravelHub (demo), Travelinkeo (real)")
print("🔑 Contraseña: viaggio1")

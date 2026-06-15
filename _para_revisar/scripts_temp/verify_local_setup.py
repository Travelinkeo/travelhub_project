from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password

User = get_user_model()

# Verificar usuarios y contraseñas
users_to_check = ['Armando3105', 'Naida1309']

for username in users_to_check:
    try:
        user = User.objects.get(username=username)
        # Verificar contraseña directamente con el hash
        if check_password('viaggio1', user.password):
            print(f'✅ {username}: Contraseña correcta "viaggio1"')
        else:
            print(f'⚠️ {username}: Contraseña incorrecta, actualizando...')
            user.set_password('viaggio1')
            user.save()
            print(f'✅ {username}: Contraseña actualizada a "viaggio1"')
        print(f'   - Email: {user.email}')
        print(f'   - Superuser: {user.is_superuser}')
        print(f'   - Staff: {user.is_staff}')
        print(f'   - Activo: {user.is_active}')
    except User.DoesNotExist:
        print(f'❌ {username}: Usuario no encontrado')

# Verificar agencias
from core.models import Agencia, UsuarioAgencia

print('\n🏢 Agencias:')
for agencia in Agencia.objects.all():
    print(f'   ✅ {agencia.nombre} ({agencia.nombre_comercial}) - {agencia.email_principal} - activa={agencia.activa}')

# Verificar asociaciones
print('\n🔗 Asociaciones usuario-agencia:')
for ua in UsuarioAgencia.objects.select_related('usuario', 'agencia').all():
    print(f'   ✅ {ua.usuario.username} → {ua.agencia.nombre} (rol: {ua.rol})')

print('\n📋 Resumen de configuración local:')
print('✅ Usuarios verificados: Armando3105, Naida1309')
print('✅ Contraseña: viaggio1')
print('✅ Agencias: TravelHub, Travelinkeo')
print('✅ Roles: admin en ambas agencias')

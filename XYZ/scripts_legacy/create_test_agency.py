from django.contrib.auth import get_user_model
from core.models import Agencia

User = get_user_model()
try:
    user = User.objects.get(username='agent')
    agencia, created = Agencia.objects.get_or_create(
        nombre='Agencia Test', 
        defaults={
            'email_principal': 'test@agencia.com',
            'nombre_comercial': 'Agencia Test Comercial',
            'rif': 'J-12345678-9',
            'propietario': user  # Added owner
        }
    )
    user.agencia = agencia
    user.save()
    print(f"SUCCESS: Assigned agency '{agencia.nombre}' (ID: {agencia.id}) to user '{user.username}'")
except Exception as e:
    print(f"ERROR: {e}")

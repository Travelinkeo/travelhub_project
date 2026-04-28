import os
import django

# Configuramos el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Agencia
from apps.crm.models_freelancer import FreelancerProfile

User = get_user_model()

def generar_freelancer_de_prueba():
    print("🚀 Iniciando creación de Freelancer de prueba...")
    
    # 1. Buscamos tu agencia principal
    agencia = Agencia.objects.first()
    if not agencia:
        print("❌ Error: No se encontró ninguna Agencia en la base de datos.")
        return

    # 2. Creamos o recuperamos el usuario
    username = 'agente_freelancer'
    password = 'travelhub2026'
    
    usuario, user_created = User.objects.get_or_create(username=username)
    usuario.set_password(password)
    usuario.first_name = 'Carlos'
    usuario.last_name = 'Freelancer'
    usuario.email = 'carlos.freelance@test.com'
    usuario.is_staff = True  # Le damos acceso para que pueda subir boletos si tu vista lo requiere
    usuario.save()

    # 3. Le creamos el perfil financiero B2B2C
    perfil, profile_created = FreelancerProfile.objects.get_or_create(
        usuario=usuario,
        defaults={
            'agencia': agencia,
            'porcentaje_comision': 50.0, # 50% de la utilidad de la agencia
            'activo': True
        }
    )

    print("-" * 40)
    print("✅ ¡Agente Externo creado y vinculado con éxito!")
    print(f"🏢 Agencia Madre: {agencia.nombre_comercial or agencia.nombre}")
    print(f"👤 Usuario: {username}")
    print(f"🔑 Contraseña: {password}")
    print(f"💰 Comisión Asignada: {perfil.porcentaje_comision}%")
    print("-" * 40)
    print("👉 Pasos para probar:")
    print("1. Cierra sesión de tu cuenta de administrador.")
    print(f"2. Inicia sesión con el usuario '{username}'.")
    print("3. Visita: http://127.0.0.1:8000/crm/portal-agente/")

if __name__ == '__main__':
    generar_freelancer_de_prueba()

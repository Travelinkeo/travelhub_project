import os
import sys
import django
from django.conf import settings

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Agencia, UsuarioAgencia, MigrationCheck
from apps.bookings.models import Venta
from personas.models import Pasajero
from core.models_catalogos import Moneda
from asgiref.sync import async_to_sync

def verify_alert():
    print("🧪 Verificando Alertas de Migración...")

    # 1. Configurar Usuario con Telegram ID
    user, _ = User.objects.get_or_create(username='test_alert_user', defaults={'email': 'alert@test.com'})
    
    # Agencia requiere propietario (non-nullable)
    agencia, _ = Agencia.objects.get_or_create(
        nombre="Agencia Alerta Test", 
        defaults={
            'propietario': user,
            'email_principal': 'test@travelhub.com'
        }
    )
    
    usuario_agencia, _ = UsuarioAgencia.objects.get_or_create(
        usuario=user, 
        agencia=agencia,
        defaults={'rol': 'admin'}
    )
    
    # Asignar ID ficticio para probar (el envío real fallará pero se logueará el intento)
    usuario_agencia.telegram_chat_id = "123456789" 
    usuario_agencia.save()
    print(f"✅ Usuario {user.username} configurado con Telegram ID: {usuario_agencia.telegram_chat_id}")

    # 2. Crear Venta
    moneda, _ = Moneda.objects.get_or_create(codigo_iso='USD', defaults={'nombre': 'Dolar'})
    venta, _ = Venta.objects.get_or_create(
        localizador="ALERTA001",
        defaults={
            'agencia': agencia,
            'creado_por': user,
            'moneda': moneda
        }
    )
    print(f"✅ Venta obtenida/creada: {venta.localizador}")

    # 3. Crear Pasajero
    pasajero, _ = Pasajero.objects.get_or_create(
        numero_documento="V00000000",
        defaults={'nombres': 'Pax', 'apellidos': 'Alerta'}
    )

    # 4. Crear MigrationCheck (Debe disparar el signal)
    print("🚀 Creando MigrationCheck crítico (RED)...")
    check = MigrationCheck.objects.create(
        pasajero=pasajero,
        venta=venta,
        origen="CCS",
        destino="USA",
        fecha_viaje="2025-01-01",
        alert_level="RED",
        visa_required=True,
        summary="Prueba de alerta automática",
        passport_validity_ok=False
    )
    
    print("✅ MigrationCheck creado.")
    print("👀 Revisa los logs de la consola o 'travelhub.log' para ver 'Alerta migratoria enviada a...'")
    print("(Nota: Como el ID 123456789 es falso, Telegram probablemente retornará error de chat not found, pero el intento cuenta)")

if __name__ == "__main__":
    verify_alert()

import os
import sys
import django
from datetime import date
from django.utils import timezone

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import MigrationCheck, Agencia
from apps.bookings.models import BoletoImportado, Venta
from personas.models import Pasajero
from core.models_catalogos import Moneda

def test_automation():
    print("🧪 PRUEBA AUTOMATIZACION MIGRACION")
    
    # 1. Crear Agencia dummy (si no existe)
    from django.contrib.auth.models import User
    user, _ = User.objects.get_or_create(username='test_automation_user', defaults={'email': 'test_auto@test.com'})
    
    agencia, _ = Agencia.objects.get_or_create(
        nombre="Agencia Test Auto", 
        defaults={
            'email_principal': 'test@test.com',
            'telefono_principal': '555-5555',
            'direccion': 'Test Address',
            'rif': 'J-12345678-9',
            'propietario': user
        }
    )
    
    # 2. Datos simulados de un boleto parseado (con vuelos)
    # Usamos un localizador único para evitar conflicto
    loc_test = f"AUTO{timezone.now().strftime('%H%M%S')}"
    
    datos_parseados = {
        'normalized': {
            'reservation_code': loc_test,
            'passenger_name': 'TEST/AUTOMATION',
            'total_amount': '100.00',
            'total_currency': 'USD',
            'flights': [
                {
                    'departure': {'location': 'CCS - Caracas'},
                    'arrival': {'location': 'MIA - Miami'},
                    'date': (timezone.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
                }
            ]
        },
        'passenger_document': 'V99999999'
    }
    
    # 3. Crear BoletoImportado
    # Importante: al guardar, se dispara la señal 'crear_o_actualizar_venta_desde_boleto'
    print(f"   Creando BoletoImportado con LOC: {loc_test}...")
    boleto = BoletoImportado.objects.create(
        datos_parseados=datos_parseados,
        agencia=agencia,
        formato_detectado="PDF"
    )
    
    # 4. Verificar si se creó la Venta
    boleto.refresh_from_db()
    venta = boleto.venta_asociada
    if not venta:
        print("❌ FALLO: No se creó la Venta asociada.")
        return

    print(f"✅ Venta creada: {venta.localizador}")
    
    # 5. Verificar si se creó el MigrationCheck
    # Puede tardar un poco si es síncrono, pero la señal es síncrona por defecto.
    checks = MigrationCheck.objects.filter(venta=venta)
    if checks.exists():
        check = checks.first()
        print(f"✅ MigrationCheck creado automáticamente!")
        print(f"   Nivel: {check.alert_level}")
        print(f"   Visa Required: {check.visa_required}")
        print(f"   Resumen: {check.summary}")
    else:
        print("❌ FALLO: No se creó el MigrationCheck automáticamente.")
        # Debug: check passengers
        pasajeros = venta.pasajeros.all()
        print(f"   Pasajeros en venta: {[p.get_nombre_completo() for p in pasajeros]}")

if __name__ == '__main__':
    import datetime # Re-import locally if needed for logic inside main/func
    test_automation()

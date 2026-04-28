"""
Script de prueba rápida del Semáforo Migratorio.

Uso:
    python scripts/test_migration_checker.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from datetime import date, timedelta
from core.services.migration_checker_service import MigrationCheckerService

def test_quick_check():
    """Prueba rápida sin base de datos"""
    print("\n" + "="*60)
    print("🧪 PRUEBA 1: Validación Rápida (sin BD)")
    print("="*60)
    
    service = MigrationCheckerService()
    
    # Caso 1: Venezolano a España (sin visa)
    print("\n📍 Caso 1: Venezolano → España")
    result = service.quick_check('VEN', 'ESP')
    print(f"   Visa requerida: {result.visa_required}")
    print(f"   Tipo: {result.visa_type}")
    print(f"   Nivel: {result.alert_level}")
    print(f"   Resumen: {result.summary}")
    
    # Caso 2: Venezolano a USA (requiere visa)
    print("\n📍 Caso 2: Venezolano → USA")
    result = service.quick_check('VEN', 'USA')
    print(f"   Visa requerida: {result.visa_required}")
    print(f"   Tipo: {result.visa_type}")
    print(f"   Nivel: {result.alert_level}")
    print(f"   Resumen: {result.summary}")
    
    # Caso 3: Venezolano a Japón (consulta Gemini)
    print("\n📍 Caso 3: Venezolano → Japón (Gemini AI)")
    result = service.quick_check('VEN', 'JPN')
    print(f"   Visa requerida: {result.visa_required}")
    print(f"   Tipo: {result.visa_type}")
    print(f"   Nivel: {result.alert_level}")
    print(f"   Resumen: {result.summary}")
    print(f"   Fuentes: {result.sources}")

def test_with_passenger():
    """Prueba con pasajero real de la BD"""
    print("\n" + "="*60)
    print("🧪 PRUEBA 2: Validación con Pasajero Real")
    print("="*60)
    
    from core.models import Pais
from apps.crm.models import Pasajero
    
    # Buscar o crear un pasajero de prueba
    try:
        pais_ven = Pais.objects.get(codigo_iso3='VEN')
    except Pais.DoesNotExist:
        print("⚠️  País Venezuela no encontrado en BD. Saltando prueba.")
        return
    
    pasajero, created = Pasajero.objects.get_or_create(
        numero_documento='TEST123456',
        defaults={
            'nombres': 'Juan',
            'apellidos': 'Pérez',
            'nacionalidad': pais_ven,
            'fecha_vencimiento_documento': date.today() + timedelta(days=365*2),  # 2 años
            'tiene_fiebre_amarilla': False
        }
    )
    
    if created:
        print(f"✅ Pasajero de prueba creado: {pasajero.get_nombre_completo()}")
    else:
        print(f"✅ Usando pasajero existente: {pasajero.get_nombre_completo()}")
    
    # Simular vuelo CCS → PTY → MAD
    vuelos = [
        {'origen': 'CCS', 'destino': 'PTY', 'fecha': date.today() + timedelta(days=30)},
        {'origen': 'PTY', 'destino': 'MAD', 'fecha': date.today() + timedelta(days=30)}
    ]
    
    service = MigrationCheckerService()
    
    print(f"\n📍 Validando: {pasajero.get_nombre_completo()} → CCS-PTY-MAD")
    check = service.check_migration_requirements(
        pasajero_id=pasajero.id_pasajero,
        vuelos=vuelos
    )
    
    print(f"\n{check.get_alert_emoji()} RESULTADO:")
    print(f"   Nivel de Alerta: {check.alert_level}")
    print(f"   Visa requerida: {check.visa_required} ({check.visa_type})")
    print(f"   Pasaporte OK: {check.passport_validity_ok}")
    print(f"   Vacunas: {', '.join(check.vaccination_required) if check.vaccination_required else 'Ninguna'}")
    print(f"   Resumen: {check.summary}")
    print(f"   Validado con IA: {'Sí' if check.checked_by_ai else 'No (regla local)'}")
    print(f"   Fecha: {check.checked_at}")

if __name__ == '__main__':
    print("\n🚦 SEMÁFORO MIGRATORIO - PRUEBAS")
    print("="*60)
    
    try:
        test_quick_check()
        test_with_passenger()
        
        print("\n" + "="*60)
        print("✅ PRUEBAS COMPLETADAS")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

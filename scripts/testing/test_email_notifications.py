"""
Script para probar el sistema completo de notificaciones
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from decimal import Decimal
from django.utils import timezone
from apps.bookings.models import Venta, PagoVenta
from core.models_catalogos import Moneda
from personas.models import Cliente

def test_notifications():
    print("=== Test Sistema de Notificaciones ===\n")
    
    # 1. Crear o buscar cliente de prueba
    cliente, created = Cliente.objects.get_or_create(
        email='travelinkeo@gmail.com',
        defaults={
            'nombres': 'Test',
            'apellidos': 'Usuario',
            'cedula_identidad': 'TEST001',
            'telefono_principal': '+582126317079'
        }
    )
    # Actualizar teléfono si ya existía
    if not created and not cliente.telefono_principal:
        cliente.telefono_principal = '+582126317079'
        cliente.save()
    print(f"{'✓ Cliente creado' if created else '✓ Cliente existente'}: {cliente.get_nombre_completo()}")
    
    # 2. Crear moneda
    moneda, _ = Moneda.objects.get_or_create(
        codigo_iso='USD',
        defaults={'nombre': 'Dólar Estadounidense', 'simbolo': '$'}
    )
    
    # 3. Crear venta (debe enviar email de confirmación)
    print("\n1. Creando venta...")
    venta = Venta.objects.create(
        cliente=cliente,
        localizador=f'TEST{timezone.now().strftime("%H%M%S")}',
        moneda=moneda,
        total_venta=Decimal('500.00'),
        saldo_pendiente=Decimal('500.00'),
        estado='PEN',
        descripcion_general='Venta de prueba para notificaciones'
    )
    print(f"   ✓ Venta creada: {venta.localizador}")
    print(f"   → Email de confirmación enviado")
    
    # 4. Cambiar estado (debe enviar email de cambio)
    print("\n2. Cambiando estado a Confirmada...")
    venta.estado = 'CNF'
    venta.save()
    print(f"   ✓ Estado cambiado a: {venta.get_estado_display()}")
    print(f"   → Email de cambio de estado enviado")
    
    # 5. Registrar pago (debe enviar email de confirmación de pago)
    print("\n3. Registrando pago...")
    pago = PagoVenta.objects.create(
        venta=venta,
        monto=Decimal('500.00'),
        moneda=moneda,
        metodo='TRF',
        confirmado=True,
        fecha_pago=timezone.now()
    )
    print(f"   ✓ Pago registrado: ${pago.monto}")
    print(f"   → Email de confirmación de pago enviado")
    
    print("\n=== Revisa tu email: travelinkeo@gmail.com ===")
    print("Deberías haber recibido 3 emails:")
    print("  1. Confirmación de venta creada")
    print("  2. Notificación de cambio de estado")
    print("  3. Confirmación de pago recibido")

if __name__ == '__main__':
    test_notifications()

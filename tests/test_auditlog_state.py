from decimal import Decimal

import pytest

from core.models.personas import Cliente
from core.models.ventas import AuditLog, Venta
from core.models_catalogos import Moneda


@pytest.mark.django_db
def test_auditlog_state_change_creates_log():
    moneda,_ = Moneda.objects.get_or_create(codigo_iso='USD', defaults={'nombre':'Dólar'})
    cliente,_ = Cliente.objects.get_or_create(nombres='Cambio', apellidos='Estado', email='estado@example.com')
    venta = Venta.objects.create(cliente=cliente, moneda=moneda, subtotal=Decimal('100.00'), impuestos=Decimal('0.00'))
    assert venta.estado == Venta.EstadoVenta.PENDIENTE_PAGO
    # Cambiar manualmente el estado a CONFIRMADA y guardar
    venta.estado = Venta.EstadoVenta.CONFIRMADA
    venta.save()
    log = AuditLog.objects.filter(modelo='Venta', accion='STATE', object_id=str(venta.pk)).order_by('-creado').first()
    assert log is not None, 'Debe existir log de cambio de estado'
    assert log.datos_previos.get('estado') == Venta.EstadoVenta.PENDIENTE_PAGO
    assert log.datos_nuevos.get('estado') == Venta.EstadoVenta.CONFIRMADA

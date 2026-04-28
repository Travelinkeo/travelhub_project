from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from core.models.personas import Cliente
from core.models.ventas import AuditLog, ItemVenta, Venta
from core.models_catalogos import Moneda, ProductoServicio


@pytest.mark.django_db
def test_auditlog_itemventa_y_venta_eliminacion():
    moneda,_ = Moneda.objects.get_or_create(codigo_iso='USD', defaults={'nombre':'Dólar'})
    cliente,_ = Cliente.objects.get_or_create(nombres='Alice', apellidos='Smith', email='alice@example.com')
    prod,_ = ProductoServicio.objects.get_or_create(nombre='Servicio Test', defaults={'tipo_producto':'GEN'})
    venta = Venta.objects.create(cliente=cliente, moneda=moneda, subtotal=Decimal('10.00'), impuestos=Decimal('2.00'))
    item = ItemVenta.objects.create(venta=venta, producto_servicio=prod, cantidad=1, precio_unitario_venta=Decimal('10.00'), impuestos_item_venta=Decimal('2.00'))

    # Intentar eliminar venta con item debe bloquear
    with pytest.raises(ValidationError):
        venta.delete()

    # Eliminar item -> genera log DELETE (además del CREATE generado al crear el item)
    item_pk = item.pk
    item.delete()
    logs_item = AuditLog.objects.filter(modelo='ItemVenta', object_id=str(item_pk))
    acciones = set(logs_item.values_list('accion', flat=True))
    assert 'CREATE' in acciones and 'DELETE' in acciones

    # Ahora eliminar venta -> genera log
    venta_pk = venta.pk
    venta.delete()
    assert AuditLog.objects.filter(modelo='Venta', object_id=str(venta_pk)).count() == 1

@pytest.mark.django_db
def test_auditlog_no_bloqueo_venta_sin_componentes():
    moneda,_ = Moneda.objects.get_or_create(codigo_iso='USD', defaults={'nombre':'Dólar'})
    cliente,_ = Cliente.objects.get_or_create(nombres='Bob', apellidos='Jones', email='bob@example.com')
    venta = Venta.objects.create(cliente=cliente, moneda=moneda, subtotal=Decimal('0.00'), impuestos=Decimal('0.00'))
    pk = venta.pk
    venta.delete()
    # Debe existir log de Venta eliminada
    assert AuditLog.objects.filter(modelo='Venta', object_id=str(pk)).exists()

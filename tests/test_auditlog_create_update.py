from decimal import Decimal

import pytest

from core.models.personas import Cliente
from core.models.ventas import AuditLog, ItemVenta, Venta
from core.models_catalogos import Moneda, ProductoServicio


@pytest.mark.django_db
def test_auditlog_venta_create_and_update():
    moneda,_ = Moneda.objects.get_or_create(codigo_iso='USD', defaults={'nombre':'Dólar'})
    cliente,_ = Cliente.objects.get_or_create(nombres='CU', apellidos='Venta', email='cuventa@example.com')
    venta = Venta.objects.create(cliente=cliente, moneda=moneda, subtotal=Decimal('10.00'), impuestos=Decimal('0.00'), descripcion_general='Desc A')
    create_log = AuditLog.objects.filter(modelo='Venta', accion='CREATE', object_id=str(venta.pk)).first()
    assert create_log is not None
    # Update tracked field
    venta.notas = 'Nueva nota'
    venta.save()
    update_log = AuditLog.objects.filter(modelo='Venta', accion='UPDATE', object_id=str(venta.pk)).order_by('-creado').first()
    assert update_log is not None
    diff = update_log.metadata_extra.get('diff') if update_log.metadata_extra else {}
    assert 'notas' in diff
    # Update untracked field (subtotal triggers recalculo pero no está en tracked diff list)
    venta.subtotal = Decimal('20.00')
    venta.save()
    # No nuevo log UPDATE sólo por subtotal
    update_logs = AuditLog.objects.filter(modelo='Venta', accion='UPDATE', object_id=str(venta.pk))
    # el último diff still should be notas only
    assert all('notas' in (log_entry.metadata_extra.get('diff') or {}) for log_entry in update_logs)

@pytest.mark.django_db
def test_auditlog_itemventa_create_and_update():
    moneda,_ = Moneda.objects.get_or_create(codigo_iso='USD', defaults={'nombre':'Dólar'})
    cliente,_ = Cliente.objects.get_or_create(nombres='CU', apellidos='Item', email='cuitem@example.com')
    prod,_ = ProductoServicio.objects.get_or_create(nombre='Servicio CU', defaults={'tipo_producto':'GEN'})
    venta = Venta.objects.create(cliente=cliente, moneda=moneda, subtotal=Decimal('0.00'), impuestos=Decimal('0.00'))
    item = ItemVenta.objects.create(venta=venta, producto_servicio=prod, cantidad=1, precio_unitario_venta=Decimal('5.00'), impuestos_item_venta=Decimal('0.00'))
    log_create = AuditLog.objects.filter(modelo='ItemVenta', accion='CREATE', object_id=str(item.pk)).first()
    assert log_create is not None
    # Update tracked field
    item.descripcion_personalizada = 'Desc Personal'
    item.save()
    log_update = AuditLog.objects.filter(modelo='ItemVenta', accion='UPDATE', object_id=str(item.pk)).order_by('-creado').first()
    assert log_update is not None
    diff = log_update.metadata_extra.get('diff') if log_update.metadata_extra else {}
    assert 'descripcion_personalizada' in diff
    # Change a non-tracked numeric field (cantidad) which is not in tracked list
    item.cantidad = 2
    item.save()
    # Ensure no new UPDATE diff includes 'cantidad'
    last_update = AuditLog.objects.filter(modelo='ItemVenta', accion='UPDATE', object_id=str(item.pk)).order_by('-creado').first()
    diff2 = last_update.metadata_extra.get('diff') if last_update.metadata_extra else {}
    assert 'cantidad' not in diff2

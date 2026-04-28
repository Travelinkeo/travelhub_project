from decimal import Decimal

import pytest
from django.urls import reverse

from core.models.personas import Cliente
from core.models.ventas import ItemVenta, Venta
from core.models_catalogos import Moneda, ProductoServicio


@pytest.mark.django_db
def test_auditlog_api_filter_create_and_update(api_client_autenticado):
    moneda,_ = Moneda.objects.get_or_create(codigo_iso='USD', defaults={'nombre':'Dólar'})
    cliente,_ = Cliente.objects.get_or_create(nombres='API', apellidos='CU', email='api_cu@example.com')
    prod,_ = ProductoServicio.objects.get_or_create(nombre='Prod API CU', defaults={'tipo_producto':'GEN'})
    venta = Venta.objects.create(cliente=cliente, moneda=moneda, subtotal=Decimal('10.00'), impuestos=Decimal('0.00'))
    venta.notas = 'Nota API'
    venta.save()
    item = ItemVenta.objects.create(venta=venta, producto_servicio=prod, cantidad=1, precio_unitario_venta=Decimal('5.00'), impuestos_item_venta=Decimal('0.00'))
    item.descripcion_personalizada = 'Desc API'
    item.save()
    url = reverse('core:audit-log-list')
    resp_create = api_client_autenticado.get(url + '?accion=CREATE')
    assert resp_create.status_code == 200
    data_create = resp_create.json()
    assert any(log_entry['accion']=='CREATE' and log_entry['modelo']=='Venta' for log_entry in data_create)
    assert any(log_entry['accion']=='CREATE' and log_entry['modelo']=='ItemVenta' for log_entry in data_create)
    resp_update = api_client_autenticado.get(url + '?accion=UPDATE')
    assert resp_update.status_code == 200
    data_update = resp_update.json()
    assert any(log_entry['accion']=='UPDATE' and log_entry['modelo']=='Venta' for log_entry in data_update)
    assert any(log_entry['accion']=='UPDATE' and log_entry['modelo']=='ItemVenta' for log_entry in data_update)

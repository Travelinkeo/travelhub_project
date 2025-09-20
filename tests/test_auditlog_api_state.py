from decimal import Decimal

import pytest
from django.urls import reverse

from core.models.personas import Cliente
from core.models.ventas import Venta
from core.models_catalogos import Moneda


@pytest.mark.django_db
def test_auditlog_api_filter_state(api_client_autenticado):
    moneda,_ = Moneda.objects.get_or_create(codigo_iso='USD', defaults={'nombre':'Dólar'})
    cliente,_ = Cliente.objects.get_or_create(nombres='Filtro', apellidos='State', email='filtrostate@example.com')
    venta = Venta.objects.create(cliente=cliente, moneda=moneda, subtotal=Decimal('50.00'), impuestos=Decimal('0.00'))
    # Cambio de estado
    venta.estado = Venta.EstadoVenta.CONFIRMADA
    venta.save()
    url = reverse('core:audit-log-list')
    resp = api_client_autenticado.get(url + '?accion=STATE&modelo=Venta')
    assert resp.status_code == 200
    data = resp.json()
    assert any(log_entry['accion'] == 'STATE' and log_entry['modelo'] == 'Venta' and log_entry['object_id'] == str(venta.pk) for log_entry in data)

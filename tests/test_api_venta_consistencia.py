import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from core.models.personas import Cliente
from core.models.ventas import Venta
from core.models_catalogos import Moneda


@pytest.mark.django_db
def test_api_venta_includes_consistency_fields():
    # Datos mínimos para crear venta
    # El modelo Cliente usa campos 'nombres' y 'apellidos'; no posee 'tipo_documento' ni 'documento'.
    cliente = Cliente.objects.create(nombres="Cliente", apellidos="Prueba", email="cliente_prueba@example.com")
    # Moneda no tiene campo 'activa'; usamos codigo_iso/nombre. Reutilizar USD si existe.
    moneda = Moneda.objects.filter(codigo_iso="USD").first() or Moneda.objects.create(codigo_iso="USD", nombre="Dolar", simbolo="$")
    venta = Venta.objects.create(
        cliente=cliente,
        moneda=moneda,
        subtotal=100,
        impuestos=15,
        total_venta=115,
        monto_pagado=0,
        saldo_pendiente=115,
        tipo_venta='BOL',
        canal_origen='WEB',
        estado='PEN'
    )

    client = APIClient()
    # Autenticar (la API requiere credenciales)
    User = get_user_model()
    User.objects.create_user(username='consistency', password='pass123', is_staff=True)
    client.login(username='consistency', password='pass123')
    resp = client.get(f"/api/ventas/{venta.id_venta}/")
    assert resp.status_code == 200, resp.content
    data = resp.json()
    # Verificar que las nuevas claves existan (aunque estén en None)
    for key in [
        'amount_consistency','amount_difference','taxes_amount_expected','taxes_difference'
    ]:
        assert key in data

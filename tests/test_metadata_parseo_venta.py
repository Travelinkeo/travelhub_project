import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from core.models.personas import Cliente
from core.models.ventas import Venta, VentaParseMetadata
from core.models_catalogos import Moneda


@pytest.mark.django_db
def test_metadata_creacion_reflejada_en_venta_detalle():
    User = get_user_model()
    User.objects.create_user(username='metauser', password='pass123', is_staff=True)
    c = APIClient()
    c.login(username='metauser', password='pass123')

    moneda = Moneda.objects.create(nombre='Dólar', codigo_iso='USD', simbolo='$')
    cliente = Cliente.objects.create(nombres='Ana', apellidos='Prueba', email='ana@example.com')
    venta = Venta.objects.create(cliente=cliente, moneda=moneda, subtotal=100, impuestos=15)

    # Al inicio los campos deben ser None
    det_ini = c.get(f'/api/ventas/{venta.id_venta}/').json()
    assert det_ini['amount_consistency'] is None

    # Crear metadata
    resp_meta = c.post('/api/ventas-metadata/', {
        'venta': venta.id_venta,
        'fuente': 'SABRE',
        'currency': 'USD',
        'fare_amount': '100.00',
        'taxes_amount': '15.00',
        'total_amount': '115.00',
        'amount_consistency': 'OK',
        'amount_difference': '0.00',
        'taxes_amount_expected': '15.00',
        'taxes_difference': '0.00',
        'segments_json': [{'origen': 'MIA', 'destino': 'LIM'}],
    }, format='json')
    assert resp_meta.status_code == 201, resp_meta.content

    det = c.get(f'/api/ventas/{venta.id_venta}/').json()
    assert det['amount_consistency'] == 'OK'
    assert det['amount_difference'] == '0.00'
    assert det['taxes_amount_expected'] == '15.00'
    assert det['taxes_difference'] == '0.00'

@pytest.mark.django_db
def test_metadata_se_toma_la_mas_reciente():
    User = get_user_model()
    User.objects.create_user(username='metauser2', password='pass123', is_staff=True)
    c = APIClient()
    c.login(username='metauser2', password='pass123')

    moneda = Moneda.objects.create(nombre='Euro', codigo_iso='EUR', simbolo='€')
    cliente = Cliente.objects.create(nombres='Luis', apellidos='Tester', email='luis@example.com')
    venta = Venta.objects.create(cliente=cliente, moneda=moneda, subtotal=200, impuestos=30)

    VentaParseMetadata.objects.create(venta=venta, fuente='KIU', fare_amount=200, taxes_amount=30, total_amount=230, amount_consistency='OK', amount_difference=0, taxes_amount_expected=30, taxes_difference=0)
    VentaParseMetadata.objects.create(venta=venta, fuente='SABRE', fare_amount=200, taxes_amount=31, total_amount=231, amount_consistency='MISMATCH', amount_difference=1, taxes_amount_expected=30, taxes_difference=1)

    det = c.get(f'/api/ventas/{venta.id_venta}/').json()
    # Debe reflejar la segunda (más reciente, fuente SABRE)
    assert det['amount_consistency'] == 'MISMATCH'
    assert det['taxes_difference'] == '1.00'

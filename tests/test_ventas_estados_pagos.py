import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from core.models import Moneda, Cliente, ProductoServicio, Venta, PagoVenta

pytestmark = pytest.mark.integration

@pytest.fixture
def api_client(db):
    User = get_user_model()
    u = User.objects.create_user(username='states', password='pass123', is_staff=True)
    c = APIClient(); c.login(username='states', password='pass123'); return c

@pytest.fixture
def moneda_usd(db):
    return Moneda.objects.create(nombre='Dólar', codigo_iso='USD', simbolo='$', es_moneda_local=False)

@pytest.fixture
def cliente(db):
    return Cliente.objects.create(nombres='Ana', apellidos='Gómez', email='ana@example.com')

@pytest.fixture
def producto(db):
    return ProductoServicio.objects.create(nombre='Servicio Test', tipo_producto=ProductoServicio.TipoProductoChoices.SERVICIO_ADICIONAL)

@pytest.fixture
def venta_base(api_client, cliente, moneda_usd, producto):
    payload = {
        'cliente': cliente.id_cliente,
        'moneda': moneda_usd.id_moneda,
        'descripcion_general': 'Venta estados',
        'impuestos': '0.00',
        'items_venta': [
            {'producto_servicio': producto.id_producto_servicio, 'cantidad': 1, 'precio_unitario_venta': '100.00', 'impuestos_item_venta': '0.00'}
        ]
    }
    resp = api_client.post('/api/ventas/', payload, format='json')
    assert resp.status_code == 201, resp.content
    return resp.json()['id_venta']

@pytest.mark.django_db
def test_estado_pasa_a_parcial_con_pago(api_client, venta_base, moneda_usd):
    # Pago parcial 40
    resp = api_client.post('/api/pagos-venta/', {
        'venta': venta_base, 'monto': '40.00', 'moneda': moneda_usd.id_moneda, 'metodo': 'TRF', 'confirmado': True
    }, format='json')
    assert resp.status_code == 201
    venta = api_client.get(f'/api/ventas/{venta_base}/').json()
    assert venta['estado'] == 'PAR'
    assert venta['saldo_pendiente'] == '60.00'

@pytest.mark.django_db
def test_estado_pasa_a_pagada_total_y_puntos(api_client, venta_base, moneda_usd, cliente):
    # Pago total 100
    resp = api_client.post('/api/pagos-venta/', {
        'venta': venta_base, 'monto': '100.00', 'moneda': moneda_usd.id_moneda, 'metodo': 'TRF', 'confirmado': True
    }, format='json')
    assert resp.status_code == 201
    venta = api_client.get(f'/api/ventas/{venta_base}/').json()
    assert venta['estado'] == 'PAG'
    # Cliente debería haber ganado puntos (100/10 = 10)
    cliente.refresh_from_db()
    assert cliente.puntos_fidelidad == 10

@pytest.mark.django_db
def test_no_duplica_puntos_con_pagos_incrementales(api_client, venta_base, moneda_usd, cliente):
    # Pago parcial 60
    r1 = api_client.post('/api/pagos-venta/', {
        'venta': venta_base, 'monto': '60.00', 'moneda': moneda_usd.id_moneda, 'metodo': 'TRF', 'confirmado': True
    }, format='json')
    assert r1.status_code == 201
    # Pago resto 40
    r2 = api_client.post('/api/pagos-venta/', {
        'venta': venta_base, 'monto': '40.00', 'moneda': moneda_usd.id_moneda, 'metodo': 'TRF', 'confirmado': True
    }, format='json')
    assert r2.status_code == 201
    cliente.refresh_from_db()
    assert cliente.puntos_fidelidad == 10
    # Un pago extra cero confirmado no aumenta puntos
    r3 = api_client.post('/api/pagos-venta/', {
        'venta': venta_base, 'monto': '0.00', 'moneda': moneda_usd.id_moneda, 'metodo': 'TRF', 'confirmado': True
    }, format='json')
    assert r3.status_code == 201
    cliente.refresh_from_db()
    assert cliente.puntos_fidelidad == 10

@pytest.mark.django_db
def test_completada_manual_antes_de_pagos_otorga_puntos_una_vez(api_client, venta_base, moneda_usd, cliente):
    # Marcamos manualmente la venta como COMPLETADA (sin pagos aún)
    patch_resp = api_client.patch(f'/api/ventas/{venta_base}/', {'estado': 'COM'}, format='json')
    assert patch_resp.status_code in (200, 202, 204), patch_resp.content
    # Recuperar venta y verificar estado
    venta = api_client.get(f'/api/ventas/{venta_base}/').json()
    assert venta['estado'] == 'COM'
    # Puntos deben haberse asignado (100/10 = 10)
    cliente.refresh_from_db()
    assert cliente.puntos_fidelidad == 10

@pytest.mark.django_db
def test_confirmada_luego_pagos_total_otorga_puntos(api_client, venta_base, moneda_usd, cliente):
    # Marcar CONFIRMADA (no debe otorgar puntos todavía porque saldo > 0)
    r = api_client.patch(f'/api/ventas/{venta_base}/', {'estado': 'CNF'}, format='json')
    assert r.status_code in (200, 202, 204), r.content
    cliente.refresh_from_db(); assert cliente.puntos_fidelidad == 0
    # Pagar total
    p = api_client.post('/api/pagos-venta/', {
        'venta': venta_base, 'monto': '100.00', 'moneda': moneda_usd.id_moneda, 'metodo': 'TRF', 'confirmado': True
    }, format='json')
    assert p.status_code == 201
    cliente.refresh_from_db(); assert cliente.puntos_fidelidad == 10
    # Campo serializer
    venta = api_client.get(f'/api/ventas/{venta_base}/').json()
    assert venta['puntos_fidelidad_asignados'] is True

@pytest.mark.django_db
def test_estado_via_no_se_sobrescribe_con_pagos(api_client, venta_base, moneda_usd, cliente):
    # Pasar a VIA (viaje en curso)
    r = api_client.patch(f'/api/ventas/{venta_base}/', {'estado': 'VIA'}, format='json')
    assert r.status_code in (200, 202, 204), r.content
    venta = api_client.get(f'/api/ventas/{venta_base}/').json(); assert venta['estado'] == 'VIA'
    # Pago parcial 50
    p1 = api_client.post('/api/pagos-venta/', {
        'venta': venta_base, 'monto': '50.00', 'moneda': moneda_usd.id_moneda, 'metodo': 'TRF', 'confirmado': True
    }, format='json'); assert p1.status_code == 201
    venta = api_client.get(f'/api/ventas/{venta_base}/').json(); assert venta['estado'] == 'VIA'
    # Pago restante 50
    p2 = api_client.post('/api/pagos-venta/', {
        'venta': venta_base, 'monto': '50.00', 'moneda': moneda_usd.id_moneda, 'metodo': 'TRF', 'confirmado': True
    }, format='json'); assert p2.status_code == 201
    venta = api_client.get(f'/api/ventas/{venta_base}/').json(); assert venta['estado'] == 'VIA'
    # Puntos asignados por saldo 0
    cliente.refresh_from_db(); assert cliente.puntos_fidelidad == 10
    # Ahora registrar pago total - no debe duplicar puntos
    pago_resp = api_client.post('/api/pagos-venta/', {
        'venta': venta_base, 'monto': '100.00', 'moneda': moneda_usd.id_moneda, 'metodo': 'TRF', 'confirmado': True
    }, format='json')
    assert pago_resp.status_code == 201
    cliente.refresh_from_db()
    assert cliente.puntos_fidelidad == 10

@pytest.mark.django_db
def test_venta_total_menor_a_10_no_otorga_puntos(api_client, cliente, moneda_usd, producto):
    # Crear venta con item de total 9.00
    payload = {
        'cliente': cliente.id_cliente,
        'moneda': moneda_usd.id_moneda,
        'descripcion_general': 'Venta pequeña',
        'impuestos': '0.00',
        'items_venta': [
            {'producto_servicio': producto.id_producto_servicio, 'cantidad': 1, 'precio_unitario_venta': '9.00', 'impuestos_item_venta': '0.00'}
        ]
    }
    resp = api_client.post('/api/ventas/', payload, format='json')
    assert resp.status_code == 201, resp.content
    v_id = resp.json()['id_venta']
    # Pagar total 9.00
    pago = api_client.post('/api/pagos-venta/', {
        'venta': v_id, 'monto': '9.00', 'moneda': moneda_usd.id_moneda, 'metodo': 'TRF', 'confirmado': True
    }, format='json')
    assert pago.status_code == 201
    cliente.refresh_from_db(); assert cliente.puntos_fidelidad == 0
    venta = api_client.get(f'/api/ventas/{v_id}/').json()
    # Debe estar pagada pero flag False (no se otorgan puntos 0)
    assert venta['estado'] == 'PAG'
    assert venta['puntos_fidelidad_asignados'] is False

@pytest.mark.django_db
def test_idempotencia_puntos_recalculo_y_pagos_extra(api_client, venta_base, moneda_usd, cliente):
    # Pagar total primero (100) -> gana 10
    p1 = api_client.post('/api/pagos-venta/', {
        'venta': venta_base, 'monto': '100.00', 'moneda': moneda_usd.id_moneda, 'metodo': 'TRF', 'confirmado': True
    }, format='json'); assert p1.status_code == 201
    cliente.refresh_from_db(); assert cliente.puntos_fidelidad == 10
    # Pago adicional (sobrepago) 20 para simular ajuste posterior
    p2 = api_client.post('/api/pagos-venta/', {
        'venta': venta_base, 'monto': '20.00', 'moneda': moneda_usd.id_moneda, 'metodo': 'TRF', 'confirmado': True
    }, format='json'); assert p2.status_code == 201
    cliente.refresh_from_db(); assert cliente.puntos_fidelidad == 10  # no aumenta
    # Recuperar venta y forzar lectura de flag
    venta = api_client.get(f'/api/ventas/{venta_base}/').json(); assert venta['puntos_fidelidad_asignados'] is True

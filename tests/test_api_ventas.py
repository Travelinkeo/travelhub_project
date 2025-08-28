import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from core.models import Moneda, Cliente, ProductoServicio, Venta, FeeVenta, PagoVenta, SegmentoVuelo, Ciudad, Pais, Proveedor
from decimal import Decimal
from django.utils import timezone

pytestmark = pytest.mark.integration

@pytest.fixture
def api_client(db):
    User = get_user_model()
    user = User.objects.create_user(username='tester', password='pass123', is_staff=True)
    client = APIClient()
    client.login(username='tester', password='pass123')
    return client

@pytest.fixture
def moneda_usd(db):
    return Moneda.objects.create(nombre='Dólar Estadounidense', codigo_iso='USD', simbolo='$', es_moneda_local=False)

@pytest.fixture
def pais_peru(db):
    return Pais.objects.create(nombre='Perú', codigo_iso_2='PE', codigo_iso_3='PER')

@pytest.fixture
def ciudad_lima(db, pais_peru):
    return Ciudad.objects.create(nombre='Lima', pais=pais_peru)

@pytest.fixture
def cliente_demo(db):
    return Cliente.objects.create(nombres='Juan', apellidos='Pérez', email='juan@example.com')

@pytest.fixture
def proveedor_demo(db):
    return Proveedor.objects.create(nombre='Proveedor X')

@pytest.fixture
def producto_boleto(db):
    return ProductoServicio.objects.create(nombre='Boleto Aéreo', tipo_producto=ProductoServicio.TipoProductoChoices.BOLETO_AEREO)

@pytest.fixture
def venta_payload(cliente_demo, moneda_usd, producto_boleto):
    return {
        'cliente': cliente_demo.id_cliente,
        'moneda': moneda_usd.id_moneda,
        'descripcion_general': 'Venta inicial test',
        'impuestos': '0.00',
        'items_venta': [
            {
                'producto_servicio': producto_boleto.id_producto_servicio,
                'cantidad': 2,
                'precio_unitario_venta': '100.00',
                'impuestos_item_venta': '10.00'
            }
        ]
    }

@pytest.mark.django_db
def test_crear_venta_con_items(api_client, venta_payload):
    resp = api_client.post('/api/ventas/', venta_payload, format='json')
    assert resp.status_code == 201, resp.content
    data = resp.json()
    # subtotal de la venta se calcula como suma de total_item_venta de cada item (precio*cantidad + impuestos_item*cantidad)
    # Item: (100 * 2) + (10 * 2) = 220
    assert data['subtotal'] == '220.00'
    # total_venta = subtotal + impuestos (campo global venta) + fees; aquí impuestos=0 y sin fees
    assert data['total_venta'] == '220.00'
    assert len(data['items_venta']) == 1

@pytest.mark.django_db
def test_agregar_fee_y_pago_recalcula(api_client, venta_payload, moneda_usd):
    # Crear venta
    resp = api_client.post('/api/ventas/', venta_payload, format='json')
    assert resp.status_code == 201
    venta_id = resp.json()['id_venta']

    # Crear fee
    fee_resp = api_client.post('/api/fees-venta/', {
        'venta': venta_id,
        'tipo_fee': 'EMI',
        'monto': '25.00',
        'moneda': moneda_usd.id_moneda,
        'es_comision_agencia': True,
        'taxable': False
    }, format='json')
    assert fee_resp.status_code == 201, fee_resp.content

    # Crear pago parcial
    pago_resp = api_client.post('/api/pagos-venta/', {
        'venta': venta_id,
        'monto': '100.00',
        'moneda': moneda_usd.id_moneda,
        'metodo': 'TRF',
        'confirmado': True
    }, format='json')
    assert pago_resp.status_code == 201, pago_resp.content

    # Refrescar venta
    venta_det = api_client.get(f'/api/ventas/{venta_id}/')
    assert venta_det.status_code == 200
    v = venta_det.json()
    # subtotal base con impuestos item: 220 (como arriba) + fee 25 => total_venta 245
    assert v['total_venta'] == '245.00'
    # saldo_pendiente = 245 - 100 = 145
    assert v['saldo_pendiente'] == '145.00'

@pytest.mark.django_db
def test_segmento_vuelo_creacion(api_client, venta_payload, ciudad_lima, cliente_demo, moneda_usd, producto_boleto):
    # Crear otra ciudad destino
    pais = ciudad_lima.pais
    ciudad_dest = Ciudad.objects.create(nombre='Cusco', pais=pais)
    # Crear venta
    resp = api_client.post('/api/ventas/', venta_payload, format='json')
    assert resp.status_code == 201
    venta_id = resp.json()['id_venta']

    seg_resp = api_client.post('/api/segmentos-vuelo/', {
        'venta': venta_id,
        'origen': ciudad_lima.id_ciudad,
        'destino': ciudad_dest.id_ciudad,
        'aerolinea': 'LA',
        'numero_vuelo': 'LA2045'
    }, format='json')
    assert seg_resp.status_code == 201, seg_resp.content

    # Ver venta y que aparece lista de segmentos
    venta_det = api_client.get(f'/api/ventas/{venta_id}/')
    assert venta_det.status_code == 200
    assert len(venta_det.json()['segmentos_vuelo']) == 1

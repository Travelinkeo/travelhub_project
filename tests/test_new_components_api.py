import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.models.personas import Cliente
from core.models.ventas import (
    AlquilerAutoReserva,
    CircuitoDia,
    CircuitoTuristico,
    EventoServicio,
    PaqueteAereo,
    ServicioAdicionalDetalle,
    Venta,
)
from core.models_catalogos import Ciudad, Moneda, Pais


@pytest.fixture
def regular_user_client(db, django_user_model):
    django_user_model.objects.create_user(username='tester', password='pass123')
    client = APIClient()
    client.login(username='tester', password='pass123')
    return client

@pytest.fixture
def staff_user_client(db, django_user_model):
    django_user_model.objects.create_user(username='staffer', password='pass123', is_staff=True)
    client = APIClient()
    client.login(username='staffer', password='pass123')
    return client

@pytest.fixture
def cliente_moneda_ciudad(db):
    pais = Pais.objects.create(nombre='Peru', codigo_iso_2='PE', codigo_iso_3='PER')
    ciudad = Ciudad.objects.create(nombre='Lima', pais=pais)
    moneda = Moneda.objects.create(nombre='Dolar', codigo_iso='USD', simbolo='$')
    cliente = Cliente.objects.create(nombres='Juan', apellidos='Perez', email='juan@example.com')
    return cliente, moneda, ciudad

@pytest.fixture
def venta_base(cliente_moneda_ciudad):
    cliente, moneda, _ = cliente_moneda_ciudad
    return Venta.objects.create(cliente=cliente, moneda=moneda, subtotal=100, impuestos=20)

@pytest.mark.django_db
def test_create_alquiler_auto_staff_ok(staff_user_client, venta_base, cliente_moneda_ciudad):
    _, _, ciudad = cliente_moneda_ciudad
    url = reverse('core:alquiler-auto-list')
    payload = {
        'venta': venta_base.id_venta,
        'ciudad_retiro': ciudad.id_ciudad,
        'ciudad_devolucion': ciudad.id_ciudad,
        'categoria_auto': 'SUV',
        'compania_rentadora': 'Hertz'
    }
    resp = staff_user_client.post(url, payload, format='json')
    assert resp.status_code == 201, resp.content
    assert AlquilerAutoReserva.objects.count() == 1

@pytest.mark.django_db
def test_create_alquiler_auto_regular_forbidden(regular_user_client, venta_base, cliente_moneda_ciudad):
    _, _, ciudad = cliente_moneda_ciudad
    url = reverse('core:alquiler-auto-list')
    payload = {
        'venta': venta_base.id_venta,
        'ciudad_retiro': ciudad.id_ciudad,
        'ciudad_devolucion': ciudad.id_ciudad,
        'categoria_auto': 'SUV',
        'compania_rentadora': 'Hertz'
    }
    resp = regular_user_client.post(url, payload, format='json')
    assert resp.status_code == 403

@pytest.mark.django_db
def test_create_evento_servicio_staff_ok(staff_user_client, venta_base):
    url = reverse('core:evento-servicio-list')
    payload = {
        'venta': venta_base.id_venta,
        'nombre_evento': 'Concierto',
        'ubicacion': 'Arena'
    }
    resp = staff_user_client.post(url, payload, format='json')
    assert resp.status_code == 201, resp.content
    assert EventoServicio.objects.count() == 1

@pytest.mark.django_db
def test_create_evento_servicio_regular_forbidden(regular_user_client, venta_base):
    url = reverse('core:evento-servicio-list')
    payload = {
        'venta': venta_base.id_venta,
        'nombre_evento': 'Concierto',
        'ubicacion': 'Arena'
    }
    resp = regular_user_client.post(url, payload, format='json')
    assert resp.status_code == 403

@pytest.mark.django_db
def test_create_circuito_con_dia_staff_ok(staff_user_client, venta_base, cliente_moneda_ciudad):
    url_circuito = reverse('core:circuito-turistico-list')
    resp_c = staff_user_client.post(url_circuito, {'venta': venta_base.id_venta, 'nombre_circuito': 'Andes Tour'}, format='json')
    assert resp_c.status_code == 201, resp_c.content
    circuito_id = resp_c.data['id_circuito']
    _, _, ciudad = cliente_moneda_ciudad
    url_dia = reverse('core:circuito-dia-list')
    resp_d = staff_user_client.post(url_dia, {'circuito': circuito_id, 'dia_numero': 1, 'titulo': 'Dia 1', 'ciudad': ciudad.id_ciudad}, format='json')
    assert resp_d.status_code == 201, resp_d.content
    assert CircuitoTuristico.objects.count() == 1
    assert CircuitoDia.objects.count() == 1

@pytest.mark.django_db
def test_create_paquete_aereo_staff_ok(staff_user_client, venta_base):
    url = reverse('core:paquete-aereo-list')
    resp = staff_user_client.post(url, {'venta': venta_base.id_venta, 'nombre_paquete': 'Promo Verano', 'noches': 5}, format='json')
    assert resp.status_code == 201, resp.content
    assert PaqueteAereo.objects.count() == 1

@pytest.mark.django_db
def test_create_paquete_aereo_regular_forbidden(regular_user_client, venta_base):
    url = reverse('core:paquete-aereo-list')
    resp = regular_user_client.post(url, {'venta': venta_base.id_venta, 'nombre_paquete': 'Promo Verano', 'noches': 5}, format='json')
    assert resp.status_code == 403

@pytest.mark.django_db
def test_create_servicio_adicional_staff_ok(staff_user_client, venta_base):
    url = reverse('core:servicio-adicional-detalle-list')
    resp = staff_user_client.post(url, {'venta': venta_base.id_venta, 'tipo_servicio': 'SEG', 'codigo_referencia': 'INS123'}, format='json')
    assert resp.status_code == 201, resp.content
    assert ServicioAdicionalDetalle.objects.count() == 1

@pytest.mark.django_db
def test_create_servicio_adicional_regular_forbidden(regular_user_client, venta_base):
    url = reverse('core:servicio-adicional-detalle-list')
    resp = regular_user_client.post(url, {'venta': venta_base.id_venta, 'tipo_servicio': 'SEG', 'codigo_referencia': 'INS123'}, format='json')
    assert resp.status_code == 403

@pytest.mark.django_db
def test_venta_serializer_includes_new_components(regular_user_client, venta_base):
    # Crear uno de cada tipo
    AlquilerAutoReserva.objects.create(venta=venta_base, categoria_auto='Sedan')
    EventoServicio.objects.create(venta=venta_base, nombre_evento='Show')
    circuito = CircuitoTuristico.objects.create(venta=venta_base, nombre_circuito='Ruta')
    CircuitoDia.objects.create(circuito=circuito, dia_numero=1)
    PaqueteAereo.objects.create(venta=venta_base, nombre_paquete='Pack')
    ServicioAdicionalDetalle.objects.create(venta=venta_base, tipo_servicio='SEG')

    url = reverse('core:venta-detail', args=[venta_base.id_venta])
    resp = regular_user_client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    for key in ['alquileres_autos','eventos_servicios','circuitos_turisticos','paquetes_aereos','servicios_adicionales']:
        assert key in data
        assert isinstance(data[key], list)

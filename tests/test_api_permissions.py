import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from core.models.personas import Cliente
from core.models.ventas import Venta
from core.models_catalogos import Moneda

pytestmark = pytest.mark.django_db

@pytest.fixture
def user() -> any:
    User = get_user_model()
    return User.objects.create_user(username='normal', password='pass123', is_staff=False)

@pytest.fixture
def staff_user() -> any:
    User = get_user_model()
    return User.objects.create_user(username='staff', password='pass123', is_staff=True)

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def venta_base(moneda_usd, cliente_demo):
    return Venta.objects.create(
        cliente=cliente_demo,
        moneda=moneda_usd,
        subtotal=0,
        impuestos=0,
        total_venta=0,
        monto_pagado=0,
        saldo_pendiente=0,
        tipo_venta='BOL',
        canal_origen='WEB',
        estado='PEN'
    )

@pytest.fixture
def moneda_usd():
    return Moneda.objects.create(nombre='USD', codigo_iso='USD', simbolo='$', es_moneda_local=False)

@pytest.fixture
def cliente_demo():
    return Cliente.objects.create(nombres='Test', apellidos='User', email='t@example.com')

# --- Health & Login endpoints are public ---

def test_health_public(api_client):
    resp = api_client.get('/api/health/')
    assert resp.status_code == 200


def test_login_public(api_client):
    resp = api_client.post('/api/auth/login/', {'username': 'x', 'password': 'y'}, format='json')
    # 401 for invalid credentials but endpoint reachable unauthenticated
    assert resp.status_code in (400, 401)

# --- Venta CRUD requires auth ---

def test_ventas_list_requires_auth(api_client):
    resp = api_client.get('/api/ventas/')
    assert resp.status_code in (401, 403)


def test_ventas_create_requires_auth(api_client, venta_payload):
    resp = api_client.post('/api/ventas/', venta_payload, format='json')
    assert resp.status_code in (401, 403)

@pytest.fixture
def venta_payload(moneda_usd, cliente_demo):
    return {
        'cliente': cliente_demo.id_cliente,
        'moneda': moneda_usd.id_moneda,
        'descripcion_general': 'Perm test',
        'impuestos': '0.00',
        'items_venta': []
    }


def test_ventas_create_authenticated(api_client, user, venta_payload):
    api_client.login(username='normal', password='pass123')
    resp = api_client.post('/api/ventas/', venta_payload, format='json')
    assert resp.status_code == 201, resp.content

# --- Admin-only action tests for AsientoContable restrictions (use metadata endpoints) ---

def test_asiento_requires_staff_for_write(api_client, user, staff_user):
    api_client.login(username='staff', password='pass123')
    from core.models_catalogos import Moneda
    m = Moneda.objects.create(nombre='EUR', codigo_iso='EUR', simbolo='€', es_moneda_local=False)
    payload = {
        'moneda': m.id_moneda,
        'fecha_contable': '2025-01-01',
        'descripcion_general': 'Asiento test',
        'detalles_asiento': []  # lista vacía permitida
    }
    resp = api_client.post('/api/asientoscontables/', payload, format='json')
    # Esperamos 201 (creado) o 400 si algún otro campo implícito resulta obligatorio; en ambos casos acceso permitido
    assert resp.status_code in (201, 400)
    api_client.logout()

    api_client.login(username='normal', password='pass123')
    resp2 = api_client.post('/api/asientoscontables/', payload, format='json')
    assert resp2.status_code in (401, 403)

# --- AuditLog read-only behavior ---

def test_audit_logs_requires_auth(api_client):
    resp = api_client.get('/api/audit-logs/')
    assert resp.status_code in (401, 403)


def test_audit_logs_read_authenticated(api_client, user):
    api_client.login(username='normal', password='pass123')
    resp = api_client.get('/api/audit-logs/')
    # Vacío pero accesible
    assert resp.status_code == 200
    assert resp.json() == []

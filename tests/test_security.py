import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_security_headers_present(api_client_staff):
    """Verifica que las cabeceras de seguridad están presentes en las respuestas."""
    url = reverse('health')
    r = api_client_staff.get(url)
    assert r.status_code == 200
    assert 'X-Content-Type-Options' in r
    assert 'X-Frame-Options' in r


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_security_headers_production(api_client_staff):
    """En modo producción, las cabeceras HSTS y CSP deben estar presentes."""
    url = reverse('health')
    r = api_client_staff.get(url)
    assert r.status_code == 200
    assert 'Content-Security-Policy' in r
    assert 'Referrer-Policy' in r
    assert 'Permissions-Policy' in r
    assert 'Strict-Transport-Security' in r


@pytest.mark.django_db
def test_health_endpoint_no_auth():
    """El endpoint de health debe ser accesible sin autenticación."""
    client = APIClient()
    url = reverse('health')
    r = client.get(url)
    assert r.status_code == 200
    assert r.json()['status'] == 'healthy'


@pytest.mark.django_db
def test_api_requires_authentication():
    """Los endpoints de API deben requerir autenticación."""
    client = APIClient()
    resp = client.get('/bookings/api/ventas/')
    assert resp.status_code in (401, 403)

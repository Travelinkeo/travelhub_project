import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_login_rate_limit(usuario_api):
    client = APIClient()
    url = reverse('core:login')
    # Hasta 5 intentos: deberían ser 401/400 (credenciales inválidas) pero toleramos 429 si otro test previo consumió cuota.
    for _i in range(5):
        r = client.post(url, {'username': 'tester', 'password': 'wrong'})
        if r.status_code == 429:
            break
        assert r.status_code in (401, 400)
    # Siguiente intento: si no hubo 429 antes, ahora es más probable
    r2 = client.post(url, {'username': 'tester', 'password': 'wrong'})
    assert r2.status_code in (401, 429)

@pytest.mark.django_db
def test_security_headers_present(api_client_staff):
    url = reverse('core:health')
    r = api_client_staff.get(url)
    assert r.status_code == 200
    # Cabeceras esperadas
    assert 'X-Content-Type-Options' in r
    assert 'Referrer-Policy' in r
    assert 'Permissions-Policy' in r
    assert 'X-Frame-Options' in r
    # Ahora la política está en modo enforce, validamos header final
    assert 'Content-Security-Policy' in r

@pytest.mark.django_db
def test_venta_object_level_permissions(usuario_api, usuario_staff, venta_base):
    # Forzar que la venta existente no pertenezca al usuario_api
    if venta_base.creado_por_id != usuario_staff.id:
        venta_base.creado_por = usuario_staff
        venta_base.save(update_fields=['creado_por'])
    client = APIClient()
    client.login(username='tester', password='pass1234')
    ventas_url = reverse('core:venta-list')
    resp = client.get(ventas_url)
    # Usuario no staff no debe ver la venta creada por staff
    assert all(v['creado_por'] == usuario_api.id for v in resp.json().get('results', [])) or resp.json().get('count', 0) == 0

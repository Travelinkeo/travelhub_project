import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_security_headers_present(api_client_staff):
    """test_security_headers_present."""
    url = reverse("health")
    r = api_client_staff.get(url)
    assert r.status_code == 200
    assert "X-Content-Type-Options" in r
    assert "X-Frame-Options" in r


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_security_headers_production(api_client_staff):
    """test_security_headers_production."""
    url = reverse("health")
    r = api_client_staff.get(url)
    assert r.status_code == 200
    assert "Content-Security-Policy" in r
    assert "Referrer-Policy" in r
    assert "Permissions-Policy" in r
    assert "Strict-Transport-Security" in r


@pytest.mark.django_db
def test_health_endpoint_no_auth():
    """test_health_endpoint_no_auth."""
    client = APIClient()
    url = reverse("health")
    r = client.get(url)
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


@pytest.mark.django_db
def test_api_requires_authentication():
    """test_api_requires_authentication."""
    client = APIClient()
    resp = client.get("/api/ventas/")
    if resp.status_code == 404:
        pytest.skip("API namespace not mounted in test environment")
    assert resp.status_code in (401, 403), f"Expected 401/403, got {resp.status_code}"

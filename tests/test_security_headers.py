"""Tests para Security headers."""
import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

SEC_HEADERS = [
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
]


@pytest.fixture
def client():
    """Client."""
    return APIClient()


@pytest.mark.django_db
def test_security_headers_and_csp_relaxed(client):
    """Security headers and csp relaxed."""
    url = reverse("health")
    r1 = client.get(url)
    assert r1.status_code == 200
    for header, expected in SEC_HEADERS:
        assert r1[header] == expected
    # Permissions-Policy should contain restricted features
    assert "geolocation=()" in r1["Permissions-Policy"]
    assert "microphone=()" in r1["Permissions-Policy"]
    assert "camera=()" in r1["Permissions-Policy"]

    # CSP present with nonce-based directives suitable for HTMX & Tailwind.
    # En paths NO-admin, 'unsafe-eval' está prohibido en script-src.
    # 'unsafe-inline' solo permitido en style-src (no en script-src).
    # Las rutas /admin/ y /system/ (Unfold, Alpine.js) son excepción documentada.
    csp1 = r1["Content-Security-Policy"]
    assert "nonce-" in csp1
    assert "strict-dynamic" in csp1
    script_part = [p.strip() for p in csp1.split(";") if p.strip().startswith("script-src")][0]
    # health/ está fuera de /admin/ → no debe tener 'unsafe-eval' ni 'unsafe-inline'
    assert "'unsafe-eval'" not in script_part
    assert "'unsafe-inline'" not in script_part
    # style-src permite 'unsafe-inline' (necesario para Django admin y Tailwind)
    style_part = [p.strip() for p in csp1.split(";") if p.strip().startswith("style-src")][0]
    assert "'unsafe-inline'" in style_part


@pytest.mark.django_db
@override_settings(DEBUG=False, SECURE_HSTS_SECONDS=31536000)
def test_hsts_when_not_debug(client):
    """Hsts when not debug."""
    url = reverse("health")
    r = client.get(url)
    assert r.status_code == 200
    # HSTS headers should be present when DEBUG False
    assert "Strict-Transport-Security" in r
    assert "max-age=31536000" in r["Strict-Transport-Security"]

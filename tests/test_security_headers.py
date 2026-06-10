import pytest
from django.conf import settings
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
    return APIClient()


@pytest.mark.django_db
def test_security_headers_and_csp_relaxed(client):
    url = reverse("health")
    r1 = client.get(url)
    assert r1.status_code == 200
    for header, expected in SEC_HEADERS:
        assert r1[header] == expected
    # Permissions-Policy should contain restricted features
    assert "geolocation=()" in r1["Permissions-Policy"]
    assert "microphone=()" in r1["Permissions-Policy"]
    assert "camera=()" in r1["Permissions-Policy"]

    # CSP present with relaxed directives suitable for HTMX & Tailwind in debug, or strict in production
    csp1 = r1["Content-Security-Policy"]
    if settings.DEBUG:
        assert "default-src 'self' 'unsafe-inline' 'unsafe-eval'" in csp1
        assert "script-src 'self' 'unsafe-inline' 'unsafe-eval'" in csp1
        assert "style-src 'self' 'unsafe-inline' 'unsafe-eval'" in csp1
    else:
        assert "nonce-" in csp1
        assert "strict-dynamic" in csp1
        assert "unsafe-inline" not in csp1


@pytest.mark.django_db
@override_settings(DEBUG=False, SECURE_HSTS_SECONDS=31536000)
def test_hsts_when_not_debug(client):
    url = reverse("health")
    r = client.get(url)
    assert r.status_code == 200
    # HSTS headers should be present when DEBUG False
    assert "Strict-Transport-Security" in r
    assert "max-age=31536000" in r["Strict-Transport-Security"]

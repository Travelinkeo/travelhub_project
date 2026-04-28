import re

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

SEC_HEADERS = [
    ('X-Content-Type-Options', 'nosniff'),
    ('X-Frame-Options', 'DENY'),
    ('Referrer-Policy', 'strict-origin-when-cross-origin'),
    # Permissions-Policy exact match may vary; we just ensure baseline directives
]

@pytest.fixture
def client():
    return APIClient()


def test_security_headers_and_csp_nonce(client):
    r1 = client.get('/api/health/')
    r2 = client.get('/api/health/')
    assert r1.status_code == 200
    for header, expected in SEC_HEADERS:
        assert r1[header] == expected
    # Permissions-Policy should contain restricted features
    assert 'geolocation=()' in r1['Permissions-Policy']
    assert 'microphone=()' in r1['Permissions-Policy']
    assert 'camera=()' in r1['Permissions-Policy']
    # CSP present with nonce and core directives
    csp1 = r1['Content-Security-Policy']
    csp2 = r2['Content-Security-Policy']
    assert "default-src 'self'" in csp1
    m1 = re.search(r"script-src 'self' 'nonce-([^']+)'", csp1)
    m2 = re.search(r"script-src 'self' 'nonce-([^']+)'", csp2)
    assert m1 and m2, 'Nonce not found in one of the CSP headers'
    nonce1, nonce2 = m1.group(1), m2.group(1)
    assert nonce1 != nonce2, 'Nonce should differ per request'
    # Report-To and report-uri presence
    assert 'Report-To' in r1
    assert 'report-uri' in csp1


@override_settings(DEBUG=False)
def test_hsts_when_not_debug(client):
    r = client.get('/api/health/')
    assert r.status_code == 200
    # HSTS headers should be present when DEBUG False (settings sets them conditionally)
    assert 'Strict-Transport-Security' in r, 'HSTS header missing in production mode simulation'

import pytest
from django.conf import settings
from django.test import Client


@pytest.mark.django_db
def test_csp_header_enforced():
    c = Client()
    resp = c.get("/login/")
    assert resp.status_code == 200
    csp = resp.headers.get("Content-Security-Policy")
    assert csp is not None, "CSP enforce header missing"
    if settings.DEBUG:
        assert "unsafe-inline" in csp
        assert "unsafe-eval" in csp
        assert "script-src 'self'" in csp
        assert "style-src 'self'" in csp
    else:
        assert "nonce-" in csp
        assert "strict-dynamic" in csp
        assert "script-src 'self'" in csp
        assert "style-src 'self'" in csp


@pytest.mark.django_db
def test_home_page_loads_with_csp(client):
    resp = client.get("/")
    assert resp.status_code in [200, 302]
    csp = resp.headers.get("Content-Security-Policy")
    assert csp
    if settings.DEBUG:
        assert "unsafe-inline" in csp
    else:
        assert "nonce-" in csp

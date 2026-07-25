"""Tests para Csp headers."""
import pytest
from django.test import Client


@pytest.mark.django_db
def test_csp_header_enforced():
    """Csp header enforced."""
    c = Client()
    resp = c.get("/login/")
    assert resp.status_code == 200
    csp = resp.headers.get("Content-Security-Policy")
    assert csp is not None, "CSP enforce header missing"
    # CSP unificado nonce-based + 'unsafe-eval' y 'unsafe-inline' requeridos por Alpine.js/HTMX/Unfold
    assert "nonce-" in csp
    assert "script-src 'self'" in csp
    assert "style-src 'self'" in csp
    script_part = [p.strip() for p in csp.split(";") if p.strip().startswith("script-src")][0]
    assert "'unsafe-eval'" in script_part
    assert "'unsafe-inline'" in script_part


@pytest.mark.django_db
def test_csp_admin_allows_unsafe_eval_for_alpine(client):
    """Csp admin allows unsafe eval for alpine."""
    resp = client.get("/admin/login/")
    csp = resp.headers.get("Content-Security-Policy")
    assert csp is not None
    script_part = [p.strip() for p in csp.split(";") if p.strip().startswith("script-src")][0]
    assert "'unsafe-eval'" in script_part
    assert "'unsafe-inline'" in script_part


@pytest.mark.django_db
def test_home_page_loads_with_csp(client):
    """Home page loads with csp."""
    resp = client.get("/")
    assert resp.status_code in [200, 302]
    csp = resp.headers.get("Content-Security-Policy")
    assert csp
    assert "nonce-" in csp

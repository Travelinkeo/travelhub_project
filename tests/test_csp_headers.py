import pytest
from django.test import Client


@pytest.mark.django_db
def test_csp_header_enforced():
    c = Client()
    resp = c.get("/login/")
    assert resp.status_code == 200
    csp = resp.headers.get("Content-Security-Policy")
    assert csp is not None, "CSP enforce header missing"
    # CSP unificado (debug + prod): nonce-based. En /login/ (no admin), sin
    # 'unsafe-eval' ni 'unsafe-inline' en script-src.
    assert "nonce-" in csp
    assert "strict-dynamic" in csp
    assert "script-src 'self'" in csp
    assert "style-src 'self'" in csp
    script_part = [p.strip() for p in csp.split(";") if p.strip().startswith("script-src")][0]
    assert "'unsafe-eval'" not in script_part
    assert "'unsafe-inline'" not in script_part


@pytest.mark.django_db
def test_csp_admin_allows_unsafe_eval_for_alpine(client):
    # /admin/ usa Unfold + Alpine.js que requiere 'unsafe-eval' para evaluar
    # bindings x-data/x-text vía new Function(). Excepción documentada en
    # SecurityHeadersMiddleware: solo /admin/ y /system/ permiten 'unsafe-eval'.
    resp = client.get("/admin/login/")
    csp = resp.headers.get("Content-Security-Policy")
    assert csp is not None
    script_part = [p.strip() for p in csp.split(";") if p.strip().startswith("script-src")][0]
    assert "'unsafe-eval'" in script_part
    # 'unsafe-inline' sigue prohibido en script-src del admin
    assert "'unsafe-inline'" not in script_part


@pytest.mark.django_db
def test_home_page_loads_with_csp(client):
    resp = client.get("/")
    assert resp.status_code in [200, 302]
    csp = resp.headers.get("Content-Security-Policy")
    assert csp
    assert "nonce-" in csp

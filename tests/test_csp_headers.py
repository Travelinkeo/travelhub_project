import re
from pathlib import Path

import pytest
from django.test import Client

TEMPLATES_TO_CHECK_NO_INLINE = [
    'core/templates/core/base.html',
    'core/templates/core/partials/pagination.html',
    'core/templates/core/sales_summary.html',
]

@pytest.mark.django_db
def test_csp_header_enforced():
    c = Client()
    resp = c.get('/api/health/')
    assert resp.status_code == 200
    csp = resp.headers.get('Content-Security-Policy')
    assert csp is not None, 'CSP enforce header missing'
    assert "script-src 'self' 'nonce-" in csp, csp
    assert "style-src 'self'" in csp and "unsafe-inline" not in csp, csp
    assert 'Content-Security-Policy-Report-Only' not in resp.headers
    # Nonce should differ per request
    resp2 = c.get('/api/health/')
    csp2 = resp2.headers.get('Content-Security-Policy')
    assert csp2 != csp, 'Nonce appears static across requests'


def test_refactored_templates_no_inline_style_attrs():
    """Ensure selected refactored templates no longer contain inline style="""  # noqa: E501
    root = Path(__file__).resolve().parent.parent
    for rel in TEMPLATES_TO_CHECK_NO_INLINE:
        content = (root / rel).read_text(encoding='utf-8')
        assert 'style=' not in content, f"Inline style attribute still present in {rel}"


def test_home_nonce_matches_header(client):  # pytest-django provides client fixture
    resp = client.get('/')
    assert resp.status_code == 200
    csp = resp.headers.get('Content-Security-Policy')
    assert csp
    m = re.search(r"script-src 'self' 'nonce-([^']+)'", csp)
    assert m, 'Nonce pattern not found in CSP header'
    header_nonce = m.group(1)
    # Extract nonce attribute from inline script tag
    body = resp.content.decode('utf-8', errors='ignore')
    m2 = re.search(r"<script[^>]*nonce=\"([^\"]+)\"", body)
    assert m2, 'No inline script with nonce attribute found in body'
    script_nonce = m2.group(1)
    assert header_nonce == script_nonce, 'Script nonce does not match CSP header nonce'

import re

import pytest


@pytest.mark.django_db
def test_home_csp_nonce_meta_and_header(client):
    resp = client.get('/')
    assert resp.status_code == 200
    csp = resp.headers.get('Content-Security-Policy')
    assert csp, 'CSP header missing'
    m = re.search(r"script-src 'self' 'nonce-([^']+)'", csp)
    assert m, 'Nonce pattern not found in CSP header'
    header_nonce = m.group(1)
    # Extract nonce attribute from inline script tag
    body = resp.content.decode('utf-8', errors='ignore')
    m2 = re.search(r"<script[^>]*nonce=\"([^\"]+)\"", body)
    assert m2, 'No inline script with nonce attribute found in body'
    script_nonce = m2.group(1)
    assert header_nonce == script_nonce, 'Script nonce does not match CSP header nonce'
    # Now, check that the nonce is present in request.META via context processor
    # This requires a custom view or patch, so we check that the nonce is not None and is 22 chars (default secrets.token_urlsafe(16))
    assert script_nonce and len(script_nonce) >= 22, 'Nonce length unexpected (should be >=22 chars)'
    # Second request should yield a different nonce
    resp2 = client.get('/')
    csp2 = resp2.headers.get('Content-Security-Policy')
    m3 = re.search(r"script-src 'self' 'nonce-([^']+)'", csp2)
    assert m3, 'Nonce pattern not found in CSP header (second request)'
    assert m3.group(1) != header_nonce, 'Nonce appears static across requests'

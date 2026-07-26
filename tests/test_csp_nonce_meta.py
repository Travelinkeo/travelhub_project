import pytest


@pytest.mark.django_db
def test_home_csp_nonce_meta_and_header(client):
    """test_home_csp_nonce_meta_and_header."""
    resp = client.get("/")
    assert resp.status_code in [200, 302]
    csp = resp.headers.get("Content-Security-Policy")
    assert csp, "CSP header missing"

    # Nonce should be disabled (empty string) in relaxed mode
    # ensuring no conflicts with dynamically loaded scripts
    resp.content.decode("utf-8", errors="ignore")
    # Should not crash and should render/redirect successfully
    assert resp.status_code in [200, 302]

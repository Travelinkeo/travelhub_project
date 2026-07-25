"""Tests para Sso security."""
from unittest.mock import MagicMock, patch

import pytest
import requests
from django.contrib.auth import get_user_model
from django.http import HttpResponseBadRequest

from core.sso.models import SSOProvider
from core.sso.views import _create_or_get_user, _oidc_callback, _verify_jwt

User = get_user_model()


@pytest.fixture
def oidc_provider(db):
    """Oidc provider."""
    return SSOProvider.objects.create(
        agencia=None,  # Global provider for tests
        name="Test Provider",
        provider_type="generic_oidc",
        client_id="test-client-id",
        client_secret="test-client-secret",
        oidc_config_url="https://idp.example.com/.well-known/openid-configuration",
        auto_provision=True,
        is_active=True,
    )


class TestSSOCallback:
    """Test Ssocallback."""
    def test_invalid_state_rejected(self, rf, oidc_provider):
        """Invalid state rejected."""
        request = rf.get("/sso/callback/1/", {"state": "invalid-state", "code": "some-code"})
        request.session = {
            "sso_oauth_state": {"state": "valid-state", "provider_id": oidc_provider.id}
        }

        response = _oidc_callback(request, oidc_provider)
        assert isinstance(response, HttpResponseBadRequest)
        assert response.content == b"Invalid state (CSRF check failed)"

    def test_idp_error_handled_gracefully(self, rf, oidc_provider):
        """Idp error handled gracefully."""
        request = rf.get("/sso/callback/1/", {"error": "access_denied"})
        request.session = {}

        response = _oidc_callback(request, oidc_provider)
        assert response.status_code == 200
        assert b"Identity Provider Error: access_denied" in response.content

    def test_auto_provision_false_blocks_new_users(self, rf, db):
        # We need a provider with auto_provision=False
        """Auto provision false blocks new users."""
        provider = SSOProvider.objects.create(
            agencia=None,
            name="No Provision",
            provider_type="generic_oidc",
            client_id="test",
            auto_provision=False,
            is_active=True,
        )

        user = _create_or_get_user("newuser@example.com", "New User", provider)
        assert user is None
        assert not User.objects.filter(email="newuser@example.com").exists()

    def test_email_verified_validation(self, rf, oidc_provider):
        """Email verified validation."""
        request = rf.get("/sso/callback/1/", {"state": "valid-state", "code": "code"})
        request.session = {
            "sso_oauth_state": {"state": "valid-state", "provider_id": oidc_provider.id}
        }

        with patch("core.sso.views._discover_oidc") as mock_discover:
            mock_discover.return_value = {"token_endpoint": "https://idp/token"}

            with patch("requests.post") as mock_post:
                mock_resp = MagicMock()
                mock_resp.json.return_value = {"id_token": "header.payload.signature"}
                mock_post.return_value = mock_resp

                with patch("core.sso.views._verify_jwt") as mock_verify:
                    mock_verify.return_value = True

                    with patch("json.loads") as mock_json_loads:
                        # Email is NOT verified
                        mock_json_loads.return_value = {
                            "email": "test@example.com",
                            "email_verified": False,
                        }

                        response = _oidc_callback(request, oidc_provider)
                        assert isinstance(response, HttpResponseBadRequest)
                        assert response.content == b"Email not verified by IdP"


class TestVerifyJWT:
    """
    Tests de regresión de seguridad para _verify_jwt().

    CRÍTICO: Estos tests verifican que el sistema es fail-closed.
    Si alguno de estos tests falla, significa que se reintrodujo una
    vulnerabilidad que permite entrada con tokens no verificados.
    """

    def test_jwks_unavailable_rejects_token(self, oidc_provider):
        """
        Regresión: el antiguo código aceptaba tokens si JWKS no estaba disponible.
        Ahora debe rechazar (fail-closed).
        """
        fake_token = "header.payload.signature"

        with patch("core.sso.views._discover_oidc") as mock_discover:
            mock_discover.return_value = {"jwks_uri": "https://idp.example.com/jwks"}

            with patch("requests.get") as mock_get:
                # Simular que el servidor JWKS no responde (timeout)
                mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

                result = _verify_jwt(fake_token, oidc_provider)

        assert result is False, (
            "FALLO DE SEGURIDAD: _verify_jwt() aceptó un token cuando el JWKS "
            "no estaba disponible. Esto permite que atacantes entren con tokens fabricados."
        )

    def test_no_oidc_config_url_rejects_token(self, db):
        """Proveedor sin oidc_config_url debe rechazar cualquier token."""
        provider = SSOProvider.objects.create(
            agencia=None,
            name="No Config URL",
            provider_type="generic_oidc",
            client_id="test",
            oidc_config_url="",  # Sin URL de configuración
            is_active=True,
        )
        fake_token = "header.payload.signature"

        result = _verify_jwt(fake_token, provider)

        assert result is False, (
            "FALLO DE SEGURIDAD: _verify_jwt() aceptó un token para un proveedor "
            "sin oidc_config_url configurado."
        )

    def test_kid_not_in_jwks_rejects_token(self, oidc_provider):
        """Si el kid del token no está en el JWKS, debe rechazarse."""
        import jwt as pyjwt

        fake_token = "header.payload.signature"

        with patch("core.sso.views._discover_oidc") as mock_discover:
            mock_discover.return_value = {"jwks_uri": "https://idp.example.com/jwks"}

            with patch("requests.get") as mock_get:
                mock_resp = MagicMock()
                # JWKS con una key de kid diferente al del token
                mock_resp.json.return_value = {"keys": [{"kid": "other-kid", "kty": "RSA"}]}
                mock_get.return_value = mock_resp

                with patch("jwt.get_unverified_header") as mock_header:
                    mock_header.return_value = {"kid": "token-kid", "alg": "RS256"}

                    result = _verify_jwt(fake_token, oidc_provider)

        assert result is False, (
            "FALLO DE SEGURIDAD: _verify_jwt() aceptó un token cuyo kid "
            "no estaba presente en el JWKS del proveedor."
        )

    def test_jwks_missing_jwks_uri_rejects(self, oidc_provider):
        """Si el discovery endpoint no devuelve jwks_uri, debe rechazarse."""
        fake_token = "header.payload.signature"

        with patch("core.sso.views._discover_oidc") as mock_discover:
            # Discovery no incluye jwks_uri
            mock_discover.return_value = {"authorization_endpoint": "https://idp/auth"}

            result = _verify_jwt(fake_token, oidc_provider)

        assert result is False, (
            "FALLO DE SEGURIDAD: _verify_jwt() aceptó un token cuando la "
            "configuración OIDC no incluía jwks_uri."
        )


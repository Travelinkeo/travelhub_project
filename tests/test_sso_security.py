from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.http import HttpResponseBadRequest

from core.sso.models import SSOProvider
from core.sso.views import _oidc_callback

User = get_user_model()


@pytest.fixture
def oidc_provider(db):
    return SSOProvider.objects.create(
        name="Test Provider",
        provider_type="generic_oidc",
        client_id="test-client-id",
        client_secret="test-client-secret",
        oidc_config_url="https://idp.example.com/.well-known/openid-configuration",
        auto_provision=True,
        is_active=True,
    )


class TestSSOCallback:
    def test_invalid_state_rejected(self, rf, oidc_provider):
        request = rf.get("/sso/callback/1/", {"state": "invalid-state", "code": "some-code"})
        request.session = {
            "sso_oauth_state": {"state": "valid-state", "provider_id": oidc_provider.id}
        }

        response = _oidc_callback(request, oidc_provider)
        assert isinstance(response, HttpResponseBadRequest)
        assert response.content == b"Invalid state (CSRF check failed)"

    def test_idp_error_handled_gracefully(self, rf, oidc_provider):
        request = rf.get("/sso/callback/1/", {"error": "access_denied"})
        request.session = {}

        response = _oidc_callback(request, oidc_provider)
        assert response.status_code == 200
        assert b"Identity Provider Error: access_denied" in response.content

    def test_auto_provision_false_blocks_new_users(self, rf, db):
        # We need a provider with auto_provision=False
        provider = SSOProvider.objects.create(
            name="No Provision",
            provider_type="generic_oidc",
            client_id="test",
            auto_provision=False,
            is_active=True,
        )

        from core.sso.views import _create_or_get_user

        user = _create_or_get_user("newuser@example.com", "New User", provider)
        assert user is None
        assert not User.objects.filter(email="newuser@example.com").exists()

    def test_email_verified_validation(self, rf, oidc_provider):
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

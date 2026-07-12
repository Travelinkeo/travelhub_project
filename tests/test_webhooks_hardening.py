"""Tests de los webhooks blindados (fail-closed).

Cubre el endurecimiento aplicado en Iteracion 2 de la auditoria:
- TelegramBotWebhookView: exige TELEGRAM_WEBHOOK_SECRET (fail-closed) y
  compara con hmac.compare_digest (timing-safe).
- BinanceWebhookView: sin BINANCE_WEBHOOK_SECRET se rechaza 503 en cualquier
  entorno (sin bypass en DEBUG); firma HMAC inválida se rechaza 401.
- StripeWebhookView: sin STRIPE_WEBHOOK_SECRET se rechaza 503; sin
  Stripe-Signature se rechaza 401; SignatureVerificationError se rechaza 401.

Estos tests validan los caminos de rechazo (fail-closed) — el camino feliz
requiere credenciales reales e integracion con proveedor y se cubre en tests
de integracion aparte.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest import mock

import pytest
from django.test import override_settings
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


# ---------------------------------------------------------------------------
# Telegram webhook
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTelegramWebhookFailClosed:
    """El webhook de Telegram debe rechazar peticiones sin WEBHOOK_SECRET."""

    def test_rechaza_cuando_secret_no_configurado(self, api_client):
        # Simula entorno sin TELEGRAM_WEBHOOK_SECRET (fail-closed).
        with override_settings(TELEGRAM_WEBHOOK_SECRET=None):
            response = api_client.post(
                "/finance/webhooks/telegram/staff-control/",
                data=json.dumps({"callback_query": {}}),
                content_type="application/json",
            )
        assert response.status_code == 403
        body = json.loads(response.content)
        assert "TELEGRAM_WEBHOOK_SECRET" in body["error"]

    def test_rechaza_cuando_secret_vacio(self, api_client):
        with override_settings(TELEGRAM_WEBHOOK_SECRET=""):
            response = api_client.post(
                "/finance/webhooks/telegram/staff-control/",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert response.status_code == 403

    def test_rechaza_cuando_secret_no_coincide(self, api_client):
        with override_settings(TELEGRAM_WEBHOOK_SECRET="valor_correcto_y_largo"):
            response = api_client.post(
                "/finance/webhooks/telegram/staff-control/",
                data=json.dumps({}),
                content_type="application/json",
                HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="valor_incorrecto",
            )
        assert response.status_code == 403

    def test_rechaza_cuando_header_no_enviado(self, api_client):
        with override_settings(TELEGRAM_WEBHOOK_SECRET="valor_correcto_y_largo"):
            response = api_client.post(
                "/finance/webhooks/telegram/staff-control/",
                data=json.dumps({}),
                content_type="application/json",
            )
        assert response.status_code == 403

    def test_acepta_cuando_secret_coincide(self, api_client):
        """Valida que con secret correcto no bloquea (payload ignorado devuelve 200)."""
        with override_settings(
            TELEGRAM_WEBHOOK_SECRET="valor_correcto_y_largo",
            TELEGRAM_BOT_TOKEN="mock_token",
        ):
            response = api_client.post(
                "/finance/webhooks/telegram/staff-control/",
                data=json.dumps({"update_id": 1}),  # sin callback_query
                content_type="application/json",
                HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="valor_correcto_y_largo",
            )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Binance webhook
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBinanceWebhookFailClosed:
    """El webhook de Binance debe rechazar peticiones sin WEBHOOK_SECRET."""

    def test_rechaza_cuando_secret_no_configurado(self, api_client):
        with override_settings(BINANCE_WEBHOOK_SECRET=None):
            response = api_client.post(
                "/finance/webhooks/binance/",
                data=json.dumps({"bizId": "bin_123", "custom_venta_id": 1, "amount": 100}),
                content_type="application/json",
            )
        assert response.status_code == 503
        body = json.loads(response.content)
        assert "Webhook not configured" in body["error"]

    def test_rechaza_cuando_secret_vacio(self, api_client):
        with override_settings(BINANCE_WEBHOOK_SECRET=""):
            response = api_client.post(
                "/finance/webhooks/binance/",
                data=json.dumps({"bizId": "bin_123"}),
                content_type="application/json",
            )
        assert response.status_code == 503

    def test_rechaza_cuando_sin_signature(self, api_client):
        with override_settings(BINANCE_WEBHOOK_SECRET="secret_largo_y_secreto"):
            response = api_client.post(
                "/finance/webhooks/binance/",
                data=json.dumps({"bizId": "bin_123", "custom_venta_id": 1, "amount": 100}),
                content_type="application/json",
            )
        assert response.status_code == 401
        body = json.loads(response.content)
        assert "Missing signature" in body["error"]

    def test_rechaza_cuando_signature_invalida(self, api_client):
        payload = json.dumps({"bizId": "bin_123", "custom_venta_id": 1, "amount": 100})
        with override_settings(BINANCE_WEBHOOK_SECRET="secret_largo_y_secreto"):
            response = api_client.post(
                "/finance/webhooks/binance/",
                data=payload,
                content_type="application/json",
                HTTP_X_BINANCE_SIGNATURE="firma_totalmente_incorrecta",
            )
        assert response.status_code == 401
        body = json.loads(response.content)
        assert "Invalid signature" in body["error"]

    def test_acepta_signature_hmac_valida_no_procesa_por_datos_malformados(self, api_client):
        """Firma válida + payload sin IDs requeridos → espera 200 (webhook malformado)."""
        payload_str = json.dumps({"bizId": "bin_123", "custom_venta_id": 1, "amount": 100})
        with override_settings(BINANCE_WEBHOOK_SECRET="secret_largo_y_secreto"):
            expected_sig = hmac.new(
                b"secret_largo_y_secreto",
                payload_str.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            response = api_client.post(
                "/finance/webhooks/binance/",
                data=payload_str,
                content_type="application/json",
                HTTP_X_BINANCE_SIGNATURE=expected_sig,
            )
        # Sin venta válida (id=1 probablemente no existe en tests limpios) → 404.
        # Lo importante: **NO** fue rechazado por signature (no 401 ni 503).
        assert response.status_code not in (401, 403, 503)

    def test_no_bypass_en_debug(self, api_client):
        """El bypass en DEBUG fue removido: even DEBUG=True no permite omitir HMAC."""
        with override_settings(
            DEBUG=True,
            BINANCE_WEBHOOK_SECRET=None,
        ):
            response = api_client.post(
                "/finance/webhooks/binance/",
                data=json.dumps({"bizId": "bin_123", "custom_venta_id": 1, "amount": 100}),
                content_type="application/json",
            )
        assert response.status_code == 503


# ---------------------------------------------------------------------------
# Stripe webhook
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestStripeWebhookFailClosed:
    """El webhook de Stripe debe rechazar peticiones sin WEBHOOK_SECRET."""

    def test_rechaza_cuando_secret_no_configurado(self, api_client):
        with override_settings(STRIPE_WEBHOOK_SECRET=None):
            response = api_client.post(
                "/finance/webhooks/stripe/",
                data=json.dumps({"id": "evt_123", "type": "payment_intent.succeeded"}),
                content_type="application/json",
            )
        assert response.status_code == 503
        body = json.loads(response.content)
        assert "Webhook not configured" in body["error"]

    def test_rechaza_cuando_secret_vacio(self, api_client):
        with override_settings(STRIPE_WEBHOOK_SECRET=""):
            response = api_client.post(
                "/finance/webhooks/stripe/",
                data=json.dumps({"id": "evt_123"}),
                content_type="application/json",
            )
        assert response.status_code == 503

    def test_rechaza_cuando_sin_signature_header(self, api_client):
        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret_largo"):
            response = api_client.post(
                "/finance/webhooks/stripe/",
                data=json.dumps({"id": "evt_123"}),
                content_type="application/json",
            )
        assert response.status_code == 401
        body = json.loads(response.content)
        assert "Missing signature" in body["error"]

    def test_rechaza_cuando_signature_invalida(self, api_client):
        with override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret_largo"):
            # Mock stripe.webhook.construct_event para lanzar SignatureVerificationError
            with mock.patch("stripe.webhook.construct_event") as mock_construct:
                import stripe

                mock_construct.side_effect = stripe.error.SignatureVerificationError(
                    "Invalid signature", "sig"
                )
                response = api_client.post(
                    "/finance/webhooks/stripe/",
                    data=json.dumps({"id": "evt_123"}),
                    content_type="application/json",
                    HTTP_STRIPE_SIGNATURE="t=123,v1=firma_invalida",
                )
        assert response.status_code == 401
        body = json.loads(response.content)
        assert "Invalid signature" in body["error"]

    def test_no_bypass_en_debug(self, api_client):
        """El bypass en DEBUG fue removido: even DEBUG=True no permite omitir firma."""
        with override_settings(
            DEBUG=True,
            STRIPE_WEBHOOK_SECRET=None,
        ):
            response = api_client.post(
                "/finance/webhooks/stripe/",
                data=json.dumps({"id": "evt_123"}),
                content_type="application/json",
            )
        assert response.status_code == 503


# ---------------------------------------------------------------------------
# Anti-regresion: verificar que el bypass DEBUG fue efectivamente removido del codigo
# (defensa contra merges accidentales que lo reinserten).
# ---------------------------------------------------------------------------


def test_bypass_debug_no_esta_en_views_webhooks():
    """Anti-regresion: el patron 'if settings.DEBUG: omitiendo HMAC' fue removido."""
    from apps.finance.views import views_webhooks

    source = open(views_webhooks.__file__, encoding="utf-8").read()
    assert "omitiendo HMAC" not in source
    assert "DEBUG), omitiendo" not in source
    # La verificacion de DEBUG dentro del bloque debe estar ausente: cualquier bypass
    # reintroducido deberia usar 'if settings.DEBUG' cerca de 'webhook_secret'.
    # En lugar de validar negativamente (frágil), validamos positivamente fail-closed.
    assert "rechazando (fail-closed)" in source

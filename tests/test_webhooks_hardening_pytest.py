#!/usr/bin/env python
"""
Phase 2 Hardening - Webhook Tests (pytest version)

Tests for webhook fail-closed behavior, HMAC validation, and anti-regression.
Run with: pytest tests/test_webhooks_hardening.py -v
"""

import hashlib
import hmac
import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.finance.views.telegram_views import _verify_telegram_webhook

User = get_user_model()


class TestTelegramWebhookFailClosed(TestCase):
    """Test Telegram webhook fail-closed behavior."""

    def setUp(self):
        """SetUp."""
        self.client = APIClient()
        self.url = reverse("finance:webhook_telegram_staff_control")

    @override_settings(TELEGRAM_WEBHOOK_SECRET=None)
    def test_rejects_when_secret_not_configured(self):
        """Fail-closed: reject if TELEGRAM_WEBHOOK_SECRET not set."""
        """Rejects when secret not configured."""
        response = self.client.post(
            self.url,
            data=json.dumps({"callback_query": {}}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertIn("TELEGRAM_WEBHOOK_SECRET", data["error"])

    @override_settings(TELEGRAM_WEBHOOK_SECRET="")
    def test_rejects_when_secret_empty(self):
        """Reject if secret is empty string."""
        """Rejects when secret empty."""
        response = self.client.post(
            self.url,
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(TELEGRAM_WEBHOOK_SECRET="correct_secret_long_enough")
    def test_rejects_when_secret_missing(self):
        """Reject if X-Telegram-Bot-Api-Secret-Token header missing."""
        response = self.client.post(
            self.url,
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(TELEGRAM_WEBHOOK_SECRET="correct_secret_long_enough")
    def test_rejects_when_secret_mismatch(self):
        """Reject if secret doesn't match."""
        response = self.client.post(
            self.url,
            data=json.dumps({}),
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="wrong_secret",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(
        TELEGRAM_WEBHOOK_SECRET="correct_secret_long_enough",
        TELEGRAM_BOT_TOKEN="mock_token",
    )
    def test_accepts_valid_secret_without_callback_query(self):
        """Accept valid secret with no callback_query (ignored update)."""
        response = self.client.post(
            self.url,
            data=json.dumps({"update_id": 1}),  # No callback_query
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="correct_secret_long_enough",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"], "ignored")

    @override_settings(
        TELEGRAM_WEBHOOK_SECRET="correct_secret_long_enough",
        TELEGRAM_BOT_TOKEN="mock_token",
    )
    @mock.patch("apps.common.tasks.answer_telegram_callback_task.delay")
    @mock.patch("apps.common.tasks.edit_telegram_message_task.delay")
    def test_accepts_valid_callback_query(self, mock_edit, mock_answer):
        """Accept valid callback_query with correct secret."""
        # Mock Pago to exist
        from apps.finance.models import Pago

        with mock.patch.object(Pago.objects, "select_for_update") as mock_select:
            mock_pago = mock.Mock()
            mock_pago.id_pago = 123
            mock_pago.confirmado = False
            mock_pago.agencia.nombre = "TEST AGENCY"
            mock_pago.venta.localizador = "LOC123"
            mock_pago.canal_recaudacion.nombre = "Efectivo"
            mock_pago.canal_recaudacion.get_tipo_display.return_value = "Efectivo"
            mock_pago.monto = "100.00"
            mock_pago.moneda.codigo_iso = "USD"
            mock_pago.igtf_monto = "0.00"
            mock_pago.igtf_aplicado = False
            mock_pago.referencia = "REF123"
            mock_pago.fecha_pago = "2024-01-15"
            mock_pago.venta.cliente = None
            mock_select.return_value.__enter__.return_value.get.return_value = mock_pago

            response = self.client.post(
                self.url,
                data=json.dumps(
                    {
                        "callback_query": {
                            "id": "callback_123",
                            "data": "pago_appr_123",
                            "message": {
                                "chat": {"id": 123456},
                                "message_id": 789,
                            },
                        }
                    }
                ),
                content_type="application/json",
                HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="correct_secret_long_enough",
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["status"], "processed")
            self.assertEqual(data["action"], "approve")

            # Verify tasks were called
            mock_answer.assert_called_once()
            mock_edit.assert_called_once()


class TestBinanceWebhookFailClosed(TestCase):
    """Test Binance webhook fail-closed behavior."""

    def setUp(self):
        """Setup."""
        self.client = APIClient()
        self.url = reverse("finance:webhook_binance_resilient")

    @override_settings(BINANCE_WEBHOOK_SECRET=None)
    def test_rejects_when_secret_not_configured(self):
        """Fail-closed: reject if BINANCE_WEBHOOK_SECRET not set."""
        response = self.client.post(
            self.url,
            data=json.dumps({"bizId": "bin_123", "custom_venta_id": 1, "amount": 100}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        data = response.json()
        self.assertIn("Webhook not configured", data["error"])

    @override_settings(BINANCE_WEBHOOK_SECRET="")
    def test_rejects_when_secret_empty(self):
        """Rejects when secret empty."""
        response = self.client.post(
            self.url,
            data=json.dumps({"bizId": "bin_123"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @override_settings(BINANCE_WEBHOOK_SECRET="secret_largo_y_secreto")
    def test_rejects_missing_signature(self):
        """Reject if X-Binance-Signature header missing."""
        response = self.client.post(
            self.url,
            data=json.dumps({"bizId": "bin_123", "custom_venta_id": 1, "amount": 100}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertIn("Missing signature", data["error"])

    @override_settings(BINANCE_WEBHOOK_SECRET="secret_largo_y_secreto")
    def test_rejects_invalid_signature(self):
        """Reject invalid HMAC signature."""
        """Rejects invalid signature."""
        payload = json.dumps({"bizId": "bin_123", "custom_venta_id": 1, "amount": 100})
        response = self.client.post(
            self.url,
            data=payload,
            content_type="application/json",
            HTTP_X_BINANCE_SIGNATURE="invalid_signature",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertIn("Invalid signature", data["error"])

    @override_settings(BINANCE_WEBHOOK_SECRET="secret_largo_y_secreto")
    def test_accepts_valid_hmac(self):
        """Accept valid HMAC-SHA256 signature."""
        payload = json.dumps({"bizId": "bin_123", "custom_venta_id": 999, "amount": "100.00"})
        expected = hmac.new(
            b"secret_largo_y_secreto",
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        with mock.patch("apps.finance.views.views_webhooks.Venta.objects") as mock_venta:
            mock_venta.filter.return_value.first.return_value = mock.Mock(pk=999)
            with mock.patch(
                "apps.finance.views.views_webhooks.TransaccionPago.objects"
            ) as mock_trans:
                mock_trans.filter.return_value.select_for_update.return_value.first.return_value = (
                    None
                )
                mock_trans.create.return_value = mock.Mock()

                response = self.client.post(
                    reverse("finance:webhook_binance_resilient"),
                    data=json.dumps(
                        {"bizId": "bin_123", "custom_venta_id": 999, "amount": "100.00"}
                    ),
                    content_type="application/json",
                    HTTP_X_BINANCE_SIGNATURE=expected,
                )

        # Should not be rejected by signature validation
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @override_settings(
        DEBUG=True,
        BINANCE_WEBHOOK_SECRET=None,
    )
    def test_no_bypass_in_debug(self):
        """Verify DEBUG=True does NOT bypass HMAC (fail-closed)."""
        response = self.client.post(
            self.url,
            data=json.dumps({"bizId": "bin_123", "custom_venta_id": 1, "amount": 100}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        # Should NOT contain "omitiendo HMAC" or similar


class TestStripeWebhookFailClosed(TestCase):
    """Test Stripe webhook fail-closed behavior."""

    def setUp(self):
        """Setup."""
        self.client = APIClient()

    @override_settings(STRIPE_WEBHOOK_SECRET=None)
    def test_rejects_when_secret_not_configured(self):
        """Rejects when secret not configured."""
        response = self.client.post(
            reverse("finance:webhook_stripe_resilient"),
            data=json.dumps({"id": "evt_123", "type": "payment_intent.succeeded"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        data = response.json()
        self.assertIn("Webhook not configured", data["error"])

    @override_settings(STRIPE_WEBHOOK_SECRET="")
    def test_rejects_empty_secret(self):
        """Rejects empty secret."""
        response = self.client.post(
            reverse("finance:webhook_stripe_resilient"),
            data=json.dumps({"id": "evt_123"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret_long")
    def test_rejects_missing_stripe_signature(self):
        """Rejects missing stripe signature."""
        response = self.client.post(
            reverse("finance:webhook_stripe_resilient"),
            data=json.dumps({"id": "evt_123"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertIn("Missing signature", data["error"])

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_secret_long")
    def test_rejects_invalid_signature(self):
        """Rejects invalid signature."""
        with mock.patch("stripe.Webhook.construct_event") as mock_construct:
            import stripe

            mock_construct.side_effect = stripe.SignatureVerificationError(
                "Invalid signature", "sig"
            )

            response = self.client.post(
                reverse("finance:webhook_stripe_resilient"),
                data=json.dumps({"id": "evt_123"}),
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="t=123,v1=invalid",
            )
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            data = response.json()
            self.assertIn("Invalid signature", data["error"])

    @override_settings(
        DEBUG=True,
        STRIPE_WEBHOOK_SECRET=None,
    )
    def test_no_bypass_in_debug(self):
        """DEBUG=True does NOT bypass signature verification."""
        response = self.client.post(
            reverse("finance:webhook_stripe_resilient"),
            data=json.dumps({"id": "evt_123"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)


class TestTelegramVerificationUnit(TestCase):
    """Unit tests for _verify_telegram_webhook function."""

    @override_settings(TELEGRAM_WEBHOOK_SECRET=None)
    def test_returns_false_when_secret_not_set(self):
        """Returns false when secret not set."""
        request = mock.Mock()
        request.headers = {}

        verified, error = _verify_telegram_webhook(request)
        self.assertFalse(verified)
        self.assertIn("TELEGRAM_WEBHOOK_SECRET", error)

    @override_settings(TELEGRAM_WEBHOOK_SECRET="")
    def test_returns_false_when_secret_empty(self):
        """Returns false when secret empty."""
        request = mock.Mock()
        request.headers = {}

        verified, error = _verify_telegram_webhook(request)
        self.assertFalse(verified)
        self.assertIn("TELEGRAM_WEBHOOK_SECRET", error)

    @override_settings(TELEGRAM_WEBHOOK_SECRET="correct_secret")
    def test_returns_false_when_header_missing(self):
        """Returns false when header missing."""
        request = mock.Mock()
        request.headers = {}

        verified, error = _verify_telegram_webhook(request)
        self.assertFalse(verified)
        self.assertEqual(error, "Secret token de Telegram inválido")

    @override_settings(TELEGRAM_WEBHOOK_SECRET="correct_secret")
    def test_returns_false_when_secret_mismatch(self):
        """Returns false when secret mismatch."""
        request = mock.Mock()
        request.headers = {"X-Telegram-Bot-Api-Secret-Token": "wrong_secret"}

        verified, error = _verify_telegram_webhook(request)
        self.assertFalse(verified)
        self.assertEqual(error, "Secret token de Telegram inválido")

    @override_settings(TELEGRAM_WEBHOOK_SECRET="correct_secret")
    def test_returns_true_when_secret_matches(self):
        """Returns true when secret matches."""
        request = mock.Mock()
        request.headers = {"X-Telegram-Bot-Api-Secret-Token": "correct_secret"}

        verified, error = _verify_telegram_webhook(request)
        self.assertTrue(verified)
        self.assertIsNone(error)

    @override_settings(TELEGRAM_WEBHOOK_SECRET="correct_secret")
    def test_uses_hmac_compare_digest(self):
        """Verify hmac.compare_digest is used (timing-safe)."""
        request = mock.Mock()
        request.headers = {"X-Telegram-Bot-Api-Secret-Token": "correct_secret"}

        with mock.patch("hmac.compare_digest", wraps=hmac.compare_digest) as mock_compare:
            verified, _ = _verify_telegram_webhook(request)
            mock_compare.assert_called_once()
            # First arg should be incoming, second should be secret
            args, _ = mock_compare.call_args
            self.assertEqual(args[0], "correct_secret")  # incoming
            self.assertEqual(args[1], "correct_secret")  # expected


class TestAntiRegressionDebugBypass(TestCase):
    """Anti-regression tests to ensure DEBUG bypass never returns."""

    def test_binance_views_no_debug_bypass(self):
        """Verify Binance webhook source has no DEBUG bypass."""
        from apps.finance.views import views_webhooks

        source = open(views_webhooks.__file__).read()

        # These patterns should NOT exist
        self.assertNotIn("omitiendo HMAC", source)
        self.assertNotIn("DEBUG), omitiendo", source)
        # Should have fail-closed logic
        self.assertIn("rechazando (fail-closed)", source)

    def test_stripe_views_no_debug_bypass(self):
        """Verify Stripe webhook source has no DEBUG bypass."""
        from apps.finance.views import views_webhooks

        source = open(views_webhooks.__file__).read()

        self.assertNotIn("omitiendo HMAC", source)
        self.assertNotIn("DEBUG), omitiendo", source)
        self.assertIn("rechazando (fail-closed)", source)

    def test_telegram_no_bot_token_fallback(self):
        """Telegram webhook no longer falls back to bot token only."""
        from apps.finance.views import telegram_views

        source = open(telegram_views.__file__, encoding="utf-8").read()

        # Old code: "Si no hay secret configurado, solo verifica que el bot_token exista"
        self.assertNotIn("solo verifica que el bot_token exista", source)
        # New code: fail-closed
        self.assertIn("fail-closed", source.lower())
        self.assertIn("TELEGRAM_WEBHOOK_SECRET no configurado", source)


# pytest configuration
pytest_plugins = ["pytest_django"]


def pytest_configure(config):
    """Pytest configure."""
    config.option.django_settings_module = "travelhub.settings"

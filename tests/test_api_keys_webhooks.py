"""
Tests para API Keys y Webhooks.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from core.models.agencia import Agencia
from core.models.api_keys import RATE_LIMITS, APIKey, APIKeyPlan
from core.models.webhooks import Webhook, WebhookDelivery, WebhookEvent


class APIKeyModelTest(TestCase):
    """Tests para el modelo APIKey."""

    def setUp(self):
        self.user = User.objects.create_user(username="test_user", password="test123")
        self.agencia = Agencia.objects.create(
            nombre="Test Agency",
            dominio="test.com",
            plan="basico",
        )

    def test_generate_api_key(self):
        """Genera una API key y retorna instance + raw_key."""
        api_key, raw_key = APIKey.generate(
            agencia=self.agencia,
            user=self.user,
            name="Test Key",
            plan=APIKeyPlan.TRIAL,
        )
        self.assertIsNotNone(raw_key)
        self.assertTrue(raw_key.startswith("th_"))
        self.assertEqual(api_key.plan, APIKeyPlan.TRIAL)
        self.assertEqual(api_key.rate_limit, 100)
        self.assertTrue(api_key.is_active)

    def test_verify_api_key(self):
        """Verifica una API key válida."""
        api_key, raw_key = APIKey.generate(
            agencia=self.agencia,
            user=self.user,
            name="Test Key",
        )
        verified = APIKey.verify(raw_key)
        self.assertIsNotNone(verified)
        self.assertEqual(verified.id, api_key.id)

    def test_verify_invalid_key(self):
        """Rechaza una API key inválida."""
        verified = APIKey.verify("invalid_key_123")
        self.assertIsNone(verified)

    def test_verify_expired_key(self):
        """Rechaza una API key expirada."""
        api_key, raw_key = APIKey.generate(
            agencia=self.agencia,
            user=self.user,
            name="Expired Key",
            expires_days=-1,  # Ya expirada
        )
        verified = APIKey.verify(raw_key)
        self.assertIsNone(verified)

    def test_revoke_api_key(self):
        """Revoca una API key."""
        api_key, raw_key = APIKey.generate(
            agencia=self.agencia,
            user=self.user,
            name="Revoke Key",
        )
        api_key.revoke()
        self.assertFalse(api_key.is_active)
        # Verificar que ya no se puede usar
        verified = APIKey.verify(raw_key)
        self.assertIsNone(verified)

    def test_update_plan(self):
        """Actualiza el plan y rate limit."""
        api_key, _ = APIKey.generate(
            agencia=self.agencia,
            user=self.user,
            name="Plan Key",
            plan=APIKeyPlan.TRIAL,
        )
        api_key.update_plan(APIKeyPlan.PROFESIONAL)
        api_key.refresh_from_db()
        self.assertEqual(api_key.plan, APIKeyPlan.PROFESIONAL)
        self.assertEqual(api_key.rate_limit, 5000)

    def test_rate_limits(self):
        """Verifica que los rate limits están correctos."""
        self.assertEqual(RATE_LIMITS[APIKeyPlan.TRIAL], 100)
        self.assertEqual(RATE_LIMITS[APIKeyPlan.BASICO], 1000)
        self.assertEqual(RATE_LIMITS[APIKeyPlan.PROFESIONAL], 5000)
        self.assertEqual(RATE_LIMITS[APIKeyPlan.ENTERPRISE], 50000)

    def test_request_count_increments(self):
        """El contador de requests se incrementa."""
        api_key, raw_key = APIKey.generate(
            agencia=self.agencia,
            user=self.user,
            name="Count Key",
        )
        self.assertEqual(api_key.request_count, 0)
        APIKey.verify(raw_key)
        api_key.refresh_from_db()
        self.assertEqual(api_key.request_count, 1)


class WebhookModelTest(TestCase):
    """Tests para el modelo Webhook."""

    def setUp(self):
        self.agencia = Agencia.objects.create(
            nombre="Test Agency",
            dominio="test.com",
            plan="basico",
        )

    def test_create_webhook(self):
        """Crea un webhook con secret automático."""
        webhook = Webhook.objects.create(
            agencia=self.agencia,
            url="https://example.com/webhook",
            events=["venta.creada", "pago.confirmado"],
        )
        self.assertIsNotNone(webhook.secret)
        self.assertTrue(webhook.is_active)
        self.assertEqual(len(webhook.events), 2)

    def test_matches_event(self):
        """Verifica si un webhook escucha un evento."""
        webhook = Webhook.objects.create(
            agencia=self.agencia,
            url="https://example.com/webhook",
            events=["venta.creada"],
        )
        self.assertTrue(webhook.matches_event("venta.creada"))
        self.assertFalse(webhook.matches_event("pago.confirmado"))

    def test_matches_all_events_when_empty(self):
        """Sin filtro = todos los eventos."""
        webhook = Webhook.objects.create(
            agencia=self.agencia,
            url="https://example.com/webhook",
            events=[],
        )
        self.assertTrue(webhook.matches_event("cualquier.evento"))

    def test_sign_payload(self):
        """Genera firma HMAC válida."""
        webhook = Webhook.objects.create(
            agencia=self.agencia,
            url="https://example.com/webhook",
        )
        payload = b'{"test": true}'
        signature = webhook.sign_payload(payload)
        self.assertEqual(len(signature), 64)  # SHA-256 hex

    def test_record_success(self):
        """Registra un envío exitoso."""
        webhook = Webhook.objects.create(
            agencia=self.agencia,
            url="https://example.com/webhook",
        )
        webhook.record_success()
        webhook.refresh_from_db()
        self.assertEqual(webhook.failure_count, 0)
        self.assertEqual(webhook.total_deliveries, 1)
        self.assertIsNotNone(webhook.last_success_at)

    def test_record_failure_disables_after_10(self):
        """Deshabilita después de 10 fallos consecutivos."""
        webhook = Webhook.objects.create(
            agencia=self.agencia,
            url="https://example.com/webhook",
        )
        for _ in range(9):
            webhook.record_failure()
        webhook.refresh_from_db()
        self.assertTrue(webhook.is_active)  # Aún activo con 9 fallos

        webhook.record_failure()
        webhook.refresh_from_db()
        self.assertFalse(webhook.is_active)  # Desactivado con 10 fallos

    def test_record_success_resets_failures(self):
        """Un éxito resetea el contador de fallos."""
        webhook = Webhook.objects.create(
            agencia=self.agencia,
            url="https://example.com/webhook",
        )
        for _ in range(5):
            webhook.record_failure()
        webhook.record_success()
        webhook.refresh_from_db()
        self.assertEqual(webhook.failure_count, 0)


class WebhookDeliveryTest(TestCase):
    """Tests para WebhookDelivery."""

    def setUp(self):
        self.agencia = Agencia.objects.create(
            nombre="Test Agency",
            dominio="test.com",
            plan="basico",
        )
        self.webhook = Webhook.objects.create(
            agencia=self.agencia,
            url="https://example.com/webhook",
            events=["venta.creada"],
        )

    def test_create_delivery(self):
        """Crea un registro de entrega."""
        delivery = WebhookDelivery.objects.create(
            webhook=self.webhook,
            event_type="venta.creada",
            payload={"venta_id": 1},
            response_status=200,
            success=True,
            duration_ms=150,
        )
        self.assertTrue(delivery.success)
        self.assertEqual(delivery.response_status, 200)

    def test_create_failed_delivery(self):
        """Crea un registro de fallo."""
        delivery = WebhookDelivery.objects.create(
            webhook=self.webhook,
            event_type="venta.creada",
            payload={"venta_id": 1},
            success=False,
            error_message="Connection timeout",
        )
        self.assertFalse(delivery.success)
        self.assertEqual(delivery.error_message, "Connection timeout")


class WebhookEventChoicesTest(TestCase):
    """Tests para los eventos disponibles."""

    def test_all_events_have_values(self):
        """Todos los eventos tienen valor y etiqueta."""
        for value, label in WebhookEvent.choices:
            self.assertIsNotNone(value)
            self.assertIsNotNone(label)
            self.assertIn(".", value)  # Formato "recurso.accion"

    def test_event_count(self):
        """Hay al menos 10 eventos disponibles."""
        self.assertGreaterEqual(len(WebhookEvent.choices), 10)

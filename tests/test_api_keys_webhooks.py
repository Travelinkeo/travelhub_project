"""
Tests para API Keys y Webhooks.
"""

from django.test import TestCase, override_settings

from core.models.agencia import Agencia
from core.models.api_keys import APIKey
from core.models.webhooks import Webhook, WebhookDelivery, WebhookEvent


class DeprecatedAPIKeyModelTest(TestCase):
    """Tests para validar que APIKey (SaaS) está deprecado."""

    def setUp(self):
        """SetUp."""
        self.agencia = Agencia.objects.create(
            nombre="Test Agency",
        )

    @override_settings(DEBUG=False)
    def test_cannot_instantiate_in_production(self):
        """Valida que APIKey no se puede instanciar en producción."""
        with self.assertRaises(RuntimeError) as context:
            APIKey(agencia=self.agencia, name="Test")
        self.assertTrue("APIKey no se puede instanciar en produccion" in str(context.exception))

    @override_settings(DEBUG=True)
    def test_can_instantiate_in_debug(self):
        """Solo para que Django no falle si necesita migrar en dev."""
        key = APIKey(agencia=self.agencia, name="Test")
        self.assertEqual(key.name, "Test")


class WebhookModelTest(TestCase):
    """Tests para el modelo Webhook."""

    def setUp(self):
        """Setup."""
        self.agencia = Agencia.objects.create(
            nombre="Test Agency",
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
        """Setup."""
        self.agencia = Agencia.objects.create(
            nombre="Test Agency",
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

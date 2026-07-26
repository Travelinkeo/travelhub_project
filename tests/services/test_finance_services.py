"""Tests para servicios financieros core — Stripe, BCV, Comisiones, Facturación."""

import unittest.mock
from decimal import Decimal

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.services]


# ─── StripeService ─────────────────────────────────────────────────


class TestStripeService:
    """TestStripeService."""

    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch):
        """_setup."""
        self.mock_stripe = unittest.mock.MagicMock()
        monkeypatch.setattr(
            "apps.finance.services.stripe_service.stripe",
            self.mock_stripe,
        )
        from apps.finance.services.stripe_service import StripeService

        self.service = StripeService()

    def test_create_checkout_session(self, db):
        """test_create_checkout_session."""
        from core.models.agencia import Agencia

        agencia = Agencia.objects.create(
            nombre="Test Agency", email_principal="a@b.com", stripe_customer_id="cus_mock"
        )
        self.mock_stripe.checkout.Session.create.return_value = unittest.mock.MagicMock(
            url="https://checkout.stripe.com/test"
        )

        url = self.service.create_checkout_session(
            agencia, "price_mock", "http://ok", "http://cancel"
        )
        assert url == "https://checkout.stripe.com/test"
        self.mock_stripe.checkout.Session.create.assert_called_once()

    def test_create_checkout_session_creates_customer(self, db):
        """test_create_checkout_session_creates_customer."""
        from core.models.agencia import Agencia

        agencia = Agencia.objects.create(nombre="New Agency", email_principal="new@b.com")
        self.mock_stripe.Customer.create.return_value = unittest.mock.MagicMock(id="cus_new")
        self.mock_stripe.checkout.Session.create.return_value = unittest.mock.MagicMock(
            url="https://checkout.stripe.com/test"
        )

        url = self.service.create_checkout_session(
            agencia, "price_mock", "http://ok", "http://cancel"
        )
        assert url == "https://checkout.stripe.com/test"
        self.mock_stripe.Customer.create.assert_called_once()

    def test_create_portal_session(self, db):
        """test_create_portal_session."""
        from core.models.agencia import Agencia

        agencia = Agencia.objects.create(
            nombre="Portal Test", email_principal="portal@b.com", stripe_customer_id="cus_portal"
        )
        self.mock_stripe.billing_portal.Session.create.return_value = unittest.mock.MagicMock(
            url="https://portal.stripe.com/test"
        )

        url = self.service.create_portal_session(agencia, "http://return")
        assert url == "https://portal.stripe.com/test"

    def test_handle_webhook(self, db, monkeypatch):
        """test_handle_webhook."""
        mock_event = unittest.mock.MagicMock()
        mock_event.type = "checkout.session.completed"
        mock_event.data.object.id = "cs_mock"
        mock_event.data.object.mode = "subscription"
        mock_event.data.object.client_reference_id = "agencia_1"
        mock_event.data.object.customer = "cus_mock"
        mock_event.data.object.subscription = "sub_mock"

        self.service.handle_webhook(mock_event)

    def test_handle_webhook_ignores_unknown_event(self, db):
        """test_handle_webhook_ignores_unknown_event."""
        mock_event = unittest.mock.MagicMock()
        mock_event.type = "unknown.event.type"

        self.service.handle_webhook(mock_event)


# ─── BCV Service ──────────────────────────────────────────────────


class TestBcvService:
    """TestBcvService."""

    def test_obtener_tasa_bcv_devuelve_tasa(self, monkeypatch):
        """test_obtener_tasa_bcv_devuelve_tasa."""
        mock_monitor = unittest.mock.MagicMock()
        mock_monitor.get_all_monitors.return_value = {
            "USD": {"price": 55.25, "price_old": 54.50},
        }
        monkeypatch.setattr(
            "apps.finance.services.bcv_service.pyDolarVenezuela",
            unittest.mock.MagicMock(),
        )
        monkeypatch.setattr(
            "apps.finance.services.bcv_service.pyDolarVenezuela.Monitor",
            lambda source: mock_monitor if source == "BCV" else unittest.mock.MagicMock(),
        )

        from apps.finance.services.bcv_service import obtener_tasa_bcv_resiliente

        result = obtener_tasa_bcv_resiliente()
        assert isinstance(result, Decimal)
        assert result > 0

    def test_obtener_tasa_bcv_fallback_en_error(self, monkeypatch):
        """test_obtener_tasa_bcv_fallback_en_error."""
        monkeypatch.setattr(
            "apps.finance.services.bcv_service.pyDolarVenezuela",
            unittest.mock.MagicMock(),
        )
        monkeypatch.setattr(
            "apps.finance.services.bcv_service.pyDolarVenezuela.Monitor",
            lambda source: (_ for _ in ()).throw(Exception("API down")),
        )

        from apps.finance.services.bcv_service import obtener_tasa_bcv_resiliente

        result = obtener_tasa_bcv_resiliente()
        assert isinstance(result, Decimal)


# ─── CommissionService ────────────────────────────────────────────


class TestCommissionService:
    """TestCommissionService."""

    def test_calcular_comision_sin_venta(self, db):
        """test_calcular_comision_sin_venta."""
        from apps.finance.services.commission_service import CommissionService

        result = CommissionService.calcular_comision_venta(99999)
        assert result is False


# ─── FacturaService ───────────────────────────────────────────────


class TestFacturaService:
    """TestFacturaService."""

    def test_capture_previous_pdf(self):
        """test_capture_previous_pdf."""
        from apps.finance.services.factura_service import FacturaService

        result = FacturaService.capture_previous_pdf(None)
        assert result is False

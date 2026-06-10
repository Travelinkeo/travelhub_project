from decimal import Decimal
from unittest.mock import patch

import pytest

from core.signals_bypass import are_signals_blocked, disable_signals

# Use pytest-django
pytestmark = pytest.mark.django_db(transaction=True)


def test_signals_bypass_context_manager():
    """
    Validates that the disable_signals context manager correctly sets the thread-local state.
    """
    assert not are_signals_blocked()

    with disable_signals():
        assert are_signals_blocked()

        # Test nesting
        with disable_signals():
            assert are_signals_blocked()

        assert are_signals_blocked()

    assert not are_signals_blocked()


@patch("apps.bookings.services.boleto_service.BoletoImportadoService.trigger_parsing_if_needed")
@patch("apps.bookings.services.boleto_service.BoletoImportadoService.post_parse_automation")
def test_boleto_importado_signals_delegation(mock_post_parse, mock_trigger, django_user_model):
    """
    Validates that saving a BoletoImportado delegates to BoletoImportadoService when signals are enabled,
    and skips it completely when they are disabled.
    """
    from apps.bookings.models import BoletoImportado
    from core.models import Agencia

    agencia = Agencia.objects.create(nombre="Test Agency")

    # --- Test Case 1: Signals Enabled (Standard Save) ---
    boleto = BoletoImportado(
        agencia=agencia, numero_boleto="9991234567890", nombre_pasajero_completo="TEST/PASSENGER"
    )

    # Save triggers signals -> delegates to service layer
    boleto.save()

    assert mock_trigger.called
    assert mock_post_parse.called

    # Reset mocks
    mock_trigger.reset_mock()
    mock_post_parse.reset_mock()

    # --- Test Case 2: Signals Disabled (Bypass Save) ---
    with disable_signals():
        boleto.nombre_pasajero_completo = "TEST/UPDATED"
        boleto.save()

    assert not mock_trigger.called
    assert not mock_post_parse.called


@patch("apps.bookings.services.venta_service.VentaService.dispatch_post_save_actions")
def test_venta_signals_delegation(mock_dispatch, django_user_model):
    """
    Validates that Venta save actions delegate to VentaService.
    """
    from apps.bookings.models import Venta
    from apps.finance.models.currencies import Moneda
    from core.models import Agencia

    agencia = Agencia.objects.create(nombre="Test Agency Venta")
    moneda, _ = Moneda.objects.get_or_create(codigo_iso="USD", defaults={"nombre": "Dolar"})

    # --- Standard Save (Delegated) ---
    venta = Venta(agencia=agencia, moneda=moneda, localizador="XYZABC")
    venta.save()

    assert mock_dispatch.called

    # Reset mock
    mock_dispatch.reset_mock()

    # --- Bypassed Save ---
    with disable_signals():
        venta.localizador = "NEWLOC"
        venta.save()

    assert not mock_dispatch.called


@patch("apps.finance.services.factura_service.FacturaService.capture_previous_pdf")
@patch("apps.finance.services.factura_service.FacturaService.send_to_telegram_if_needed")
def test_factura_signals_delegation(mock_send, mock_capture, django_user_model):
    """
    Validates that Factura pre_save and post_save hooks delegate to FacturaService.
    """
    from apps.bookings.models import Venta
    from apps.crm.models import Cliente
    from apps.finance.models import Factura
    from apps.finance.models.currencies import Moneda
    from core.models import Agencia

    agencia = Agencia.objects.create(nombre="Test Agency Factura")
    moneda, _ = Moneda.objects.get_or_create(codigo_iso="USD", defaults={"nombre": "Dolar"})
    cliente = Cliente.objects.create(
        agencia=agencia, nombres="Cliente Test", apellidos="Factura", cedula_identidad="V-12345678"
    )
    venta = Venta.objects.create(
        agencia=agencia, moneda=moneda, localizador="XYZFAC", cliente=cliente
    )

    factura = Factura(
        venta_asociada=venta,
        cliente=cliente,
        moneda=moneda,
        agencia=agencia,
        tasa_cambio_bcv=Decimal("36.0"),
    )

    factura.save()

    assert mock_capture.called
    assert mock_send.called

    # Reset mocks
    mock_capture.reset_mock()
    mock_send.reset_mock()

    # --- Bypassed Save ---
    with disable_signals():
        factura.save()

    assert not mock_capture.called
    assert not mock_send.called


@patch("apps.crm.services.migration_service.MigrationService.trigger_migration_alert_if_needed")
def test_migration_check_signals_delegation(mock_migration, django_user_model):
    """
    Validates that MigrationCheck post_save delegates to MigrationService.
    """
    from apps.crm.models import Pasajero
    from core.models import Agencia, MigrationCheck

    agencia = Agencia.objects.create(nombre="Test Agency Migra")
    pasajero = Pasajero.objects.create(
        agencia=agencia, nombres="Juan", apellidos="Perez", cedula_identidad="V-999999"
    )

    check = MigrationCheck(pasajero=pasajero, alert_level="RED")
    check.save()

    assert mock_migration.called

    # Reset mock
    mock_migration.reset_mock()

    # --- Bypassed Save ---
    with disable_signals():
        check.save()

    assert not mock_migration.called

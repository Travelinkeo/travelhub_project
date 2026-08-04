import pytest

from apps.bookings.models import BoletoImportado

# SKIP REMOVIDO - reactivado


@pytest.mark.django_db
def test_create_boleto_with_financial_fields():
    """test_create_boleto_with_financial_fields."""
    # Crear boleto vía modelo directamente (simulación import)
    boleto = BoletoImportado.objects.create(
        numero_boleto="1234567890123",
        tarifa_base=100,
        impuestos_total_calculado=20,
        total_boleto=120,
        exchange_monto=5,
        void_monto=0,
        fee_servicio=10,
        igtf_monto=2,
        comision_agencia=8,
        estado_parseo=BoletoImportado.EstadoParseo.COMPLETADO,
    )
    assert boleto.exchange_monto == 5
    assert boleto.comision_agencia == 8
    assert boleto.fee_servicio == 10
    assert boleto.igtf_monto == 2

    # Actualización directa de campos financieros
    boleto.tarifa_base = 150
    boleto.impuestos_total_calculado = 30
    boleto.total_boleto = 180
    boleto.exchange_monto = 7
    boleto.save(
        update_fields=["tarifa_base", "impuestos_total_calculado", "total_boleto", "exchange_monto"]
    )
    boleto.refresh_from_db()
    assert str(boleto.tarifa_base) == "150.00"
    assert str(boleto.impuestos_total_calculado) == "30.00"
    assert str(boleto.total_boleto) == "180.00"
    assert str(boleto.exchange_monto) == "7.00"

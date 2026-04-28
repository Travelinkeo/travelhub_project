import pytest
from django.urls import reverse

from core.models.boletos import BoletoImportado

pytestmark = pytest.mark.django_db


def test_create_boleto_with_financial_fields(client):
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
        estado_parseo=BoletoImportado.EstadoParseo.COMPLETADO
    )
    assert boleto.exchange_monto == 5
    assert boleto.comision_agencia == 8

    # Editar vía vista editable
    url = reverse('core:air_tickets_editable')
    response_get = client.get(url)
    assert response_get.status_code == 200

    post_data = {
        'boleto_id': boleto.id_boleto_importado,
        'tarifa_base': '150.00',
        'impuestos_total_calculado': '30.00',
        'total_boleto': '180.00',
        'exchange_monto': '7.00',
        'void_monto': '1.50',
        'fee_servicio': '12.00',
        'igtf_monto': '3.25',
        'comision_agencia': '9.00',
    }
    response_post = client.post(url, post_data, follow=True)
    assert response_post.status_code == 200

    boleto.refresh_from_db()
    assert str(boleto.tarifa_base) == '150.00'
    assert str(boleto.impuestos_total_calculado) == '30.00'
    assert str(boleto.total_boleto) == '180.00'
    assert str(boleto.exchange_monto) == '7.00'
    assert str(boleto.void_monto) == '1.50'
    assert str(boleto.fee_servicio) == '12.00'
    assert str(boleto.igtf_monto) == '3.25'
    assert str(boleto.comision_agencia) == '9.00'

from apps.bookings.models import BoletoImportado


def test_boleto_importado_pk_id_alias():
    """Verifica que el alias 'id' funciona como getter y setter correcto de BoletoImportado en memoria"""
    # Creamos la instancia en memoria sin persistir en base de datos
    boleto = BoletoImportado(
        id_boleto_importado=1234,
        numero_boleto="999-1234567890",
        nombre_pasajero_completo="DOE/JOHN",
    )

    # 1. Comprobar que el getter funciona y coincide con id_boleto_importado
    assert boleto.id == 1234
    assert boleto.id == boleto.id_boleto_importado

    # 2. Comprobar que podemos usar 'id' como alias setter
    boleto.id = 9999
    assert boleto.id_boleto_importado == 9999
    assert boleto.id == 9999

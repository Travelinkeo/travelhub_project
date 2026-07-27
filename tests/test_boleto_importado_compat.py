from apps.bookings.models import BoletoImportado


def test_boleto_importado_pk_alias():
    """Verifica que pk e id_boleto_importado son equivalentes."""
    boleto = BoletoImportado(
        id_boleto_importado=1234,
        numero_boleto="999-1234567890",
        nombre_pasajero_completo="DOE/JOHN",
    )
    assert boleto.pk == 1234
    assert boleto.pk == boleto.id_boleto_importado


def test_boleto_importado_no_id_property():
    """Verifica que NO existe un @property id (P2-007 fix)."""
    boleto = BoletoImportado(id_boleto_importado=1234)
    assert not hasattr(boleto, "id"), (
        "El @property id fue eliminado — usar pk o id_boleto_importado"
    )

import pytest

from apps.finance.models_stubs import CanalRecaudacion


@pytest.mark.django_db
class TestEngineRecaudacionFiscal:
    """TestEngineRecaudacionFiscal."""

    def test_canal_crud(self, agencia_premium, moneda_usd):
        """Test básico de creación y filtrado de CanalRecaudacion."""
        canal = CanalRecaudacion.objects.create(
            nombre="Caja Fuerte Premium",
            tipo=CanalRecaudacion.TipoCanal.EFECTIVO,
            moneda=moneda_usd,
            agencia=agencia_premium,
        )
        assert canal.pk is not None
        assert CanalRecaudacion.objects.filter(agencia=agencia_premium).count() == 1

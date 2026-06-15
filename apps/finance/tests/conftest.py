import pytest
from django.conf import settings


def pytest_configure(config):
    settings.DATABASES["default"]["HOST"] = "db"
    settings.DATABASES["default"]["PORT"] = 5432


@pytest.fixture
def agencia_premium(db):
    from core.models.agencia import Agencia

    agencia = Agencia.objects.create(
        nombre="Turismo Premium LatAn", email_principal="premium@travelhub.cc"
    )
    config = agencia.configuracion
    config.es_sujeto_pasivo_especial = True
    config.subdominio_slug = "premium"
    config.save()
    return agencia


@pytest.fixture
def agencia_estandar(db):
    from core.models.agencia import Agencia

    agencia = Agencia.objects.create(
        nombre="Viajes Estándar", email_principal="estandar@travelhub.cc"
    )
    config = agencia.configuracion
    config.es_sujeto_pasivo_especial = False
    config.subdominio_slug = "estandar"
    config.save()
    return agencia


@pytest.fixture
def moneda_usd(db):
    from apps.finance.models.currencies import Moneda

    moneda, _ = Moneda.objects.get_or_create(
        codigo_iso="USD", defaults={"nombre": "Dólar Americano", "simbolo": "$"}
    )
    return moneda

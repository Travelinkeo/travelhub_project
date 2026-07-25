"""Configuración de pruebas (pytest) para finance.
"""

import pytest
from django.conf import settings


def pytest_configure(config):
    # pytest_configure: Pytest configure. Args: según implementación. Returns: según implementación.
    settings.DATABASES["default"]["HOST"] = "db"
    settings.DATABASES["default"]["PORT"] = 5432


@pytest.fixture
def agencia_premium(db):
    # agencia_premium: Agencia premium. Args: según implementación. Returns: según implementación.
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
    # agencia_estandar: Agencia estandar. Args: según implementación. Returns: según implementación.
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
    # moneda_usd: Moneda usd. Args: según implementación. Returns: según implementación.
    from apps.common.models import Moneda

    moneda, _ = Moneda.objects.get_or_create(
        codigo_iso="USD", defaults={"nombre": "Dólar Americano", "simbolo": "$"}
    )
    return moneda

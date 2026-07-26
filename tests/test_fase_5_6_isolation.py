from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.finance.models_stubs import TasaCambio
from apps.marketing.models import Campania
from core.middleware import agency_context
from core.models import Agencia

pytestmark = pytest.mark.skip(reason="Tests requieren configuración completa o refactorización")


@pytest.fixture
def agencias_test(db):
    """agencias_test."""
    agencia_a = Agencia.objects.create(nombre="Agencia A", rif="J123456789")
    agencia_b = Agencia.objects.create(nombre="Agencia B", rif="J987654321")
    return agencia_a, agencia_b


@pytest.mark.django_db
def test_marketing_isolation(agencias_test):
    """test_marketing_isolation."""
    agencia_a, agencia_b = agencias_test

    # Crear campaña para Agencia A
    with agency_context(agencia_a):
        Campania.objects.create(nombre="Promo Verano A", agencia=agencia_a)

    # Crear campaña para Agencia B
    with agency_context(agencia_b):
        Campania.objects.create(nombre="Promo Invierno B", agencia=agencia_b)

    # Verificar aislamiento en Agencia A
    with agency_context(agencia_a):
        assert Campania.objects.count() == 1
        assert Campania.objects.first().nombre == "Promo Verano A"

    # Verificar aislamiento en Agencia B
    with agency_context(agencia_b):
        assert Campania.objects.count() == 1
        assert Campania.objects.first().nombre == "Promo Invierno B"

    # Sin contexto (retorna vacío por seguridad)
    with agency_context(None):
        assert Campania.objects.count() == 0


@pytest.mark.django_db
def test_bcv_scraper_fallback_mock():
    """test_bcv_scraper_fallback_mock."""
    from apps.finance.services.bcv_scraper import obtener_tasas_bcv

    # Mock de requests para que falle el sitio del BCV
    with patch("requests.get") as mock_get:
        mock_get.side_effect = Exception("BCV Down")

        # Mock de DolarApi (primer fallback)
        with patch("apps.finance.services.bcv_scraper._obtener_tasas_dolarapi") as mock_dolarapi:
            mock_dolarapi.return_value = {"USD": Decimal("45.50")}

            tasas = obtener_tasas_bcv()

            assert "USD" in tasas
            assert tasas["USD"] == Decimal("45.50")
            assert mock_dolarapi.called


@pytest.mark.django_db
def test_agencia_form_save(agencias_test, sample_pais):
    """test_agencia_form_save."""
    from core.forms.agencia_forms import AgenciaSettingsForm
    from core.models import AgenciaBranding, AgenciaConfiguracion

    agencia_a, _ = agencias_test

    data = {
        "nombre_comercial": "Agencia Editada",
        "rif": "J000000001",
        "email_principal": "admin@agencia.com",
        "pais": sample_pais.id_pais,
        "color_primario": "#FF5733",
        "zona_horaria": "America/Caracas",
        "moneda_principal": "VES",
    }

    form = AgenciaSettingsForm(data=data, instance=agencia_a)
    assert form.is_valid(), form.errors

    form.save()

    # Verificar que se crearon los componentes satélite
    assert AgenciaBranding.objects.filter(agencia=agencia_a).exists()
    assert AgenciaConfiguracion.objects.filter(agencia=agencia_a).exists()

    branding = AgenciaBranding.objects.get(agencia=agencia_a)
    assert branding.color_primario == "#FF5733"

    config = AgenciaConfiguracion.objects.get(agencia=agencia_a)
    assert config.zona_horaria == "America/Caracas"


@pytest.mark.django_db
def test_bcv_resilient_service_survival_cache():
    """test_bcv_resilient_service_survival_cache."""
    from datetime import date

    from apps.finance.services.bcv_service import obtener_tasa_bcv_resiliente

    # 1. Preparar caché de supervivencia
    TasaCambio.objects.create(fecha=date(2026, 1, 1), moneda="USD", monto=Decimal("35.50"))

    # 2. Forzar fallo en el monitor de pyDolarVenezuela
    with patch("apps.finance.services.bcv_service.Monitor") as mock_monitor_cls:
        mock_monitor = mock_monitor_cls.return_value
        mock_monitor.get_all_monitors.side_effect = Exception("BCV Dead")

        # 3. Mock de telegram para no enviar mensajes reales
        with patch("apps.finance.services.bcv_service.enviar_alerta_telegram") as mock_telegram:
            tasa = obtener_tasa_bcv_resiliente("USD")

            # Debe retornar la del caché
            assert tasa == 35.50
            assert mock_telegram.called

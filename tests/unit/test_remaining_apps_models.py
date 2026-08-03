"""Tests para modelos de apps restantes: cotizaciones, crm, gamification, marketing, reports, tasks, cms."""

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.models]


class TestCotizacionesModels:
    """TestCotizacionesModels."""

    def test_cotizacion_creation(self, db):
        """test_cotizacion_creation."""
        from apps.cotizaciones.models import Cotizacion
        from tests.helpers import create_test_agencia, create_test_cliente, create_test_moneda

        agencia = create_test_agencia()
        cliente = create_test_cliente()
        moneda = create_test_moneda()
        cotizacion = Cotizacion.objects.create(
            agencia=agencia,
            cliente=cliente,
            moneda=moneda,
            estado="BOR",
        )
        assert cotizacion.id_cotizacion is not None
        assert str(cotizacion) is not None


class TestGamificationModels:
    """TestGamificationModels."""

    def test_puntuacion_creation(self, db):
        """test_puntuacion_creation."""
        from apps.gamification.models import PuntuacionUsuario
        from tests.helpers import create_test_agencia, create_test_user

        agencia = create_test_agencia()
        usuario = create_test_user()
        puntuacion = PuntuacionUsuario.objects.create(
            agencia=agencia,
            usuario=usuario,
            puntos_total=100,
        )
        assert puntuacion.id is not None

    def test_logro_creation(self, db):
        """test_logro_creation."""
        from apps.gamification.models import Logro

        logro = Logro.objects.create(
            codigo="test-achievement",
            nombre="Test Achievement",
            descripcion="Test description",
            icono="emoji_events",
        )
        assert logro.id is not None


class TestMarketingModels:
    """TestMarketingModels."""

    def test_campania_creation(self, db):
        """test_campania_creation."""
        from apps.marketing.models import Campania
        from tests.helpers import create_test_agencia

        agencia = create_test_agencia()
        campania = Campania.objects.create(
            agencia=agencia,
            nombre="Test Campaign",
            estado="BORRADOR",
        )
        assert campania.id is not None


class TestReportsModels:
    """TestReportsModels."""

    def test_reporte_programado_creation(self, db):
        """test_reporte_programado_creation."""
        from apps.reports.models import ReporteProgramado
        from tests.helpers import create_test_agencia

        agencia = create_test_agencia()
        reporte = ReporteProgramado.objects.create(
            agencia=agencia,
            nombre="Test Report",
            tipo="ventas",
            frecuencia="diario",
            activo=True,
        )
        assert reporte.id is not None


class TestTasksModels:
    """TestTasksModels."""

    def test_tarea_creation(self, db):
        """test_tarea_creation."""
        from apps.tasks.models import Tarea
        from tests.helpers import create_test_agencia, create_test_user

        agencia = create_test_agencia()
        usuario = create_test_user()
        tarea = Tarea.objects.create(
            agencia=agencia,
            titulo="Test Task",
            descripcion="Test",
            asignado_a=usuario,
            creado_por=usuario,
            prioridad="media",
            estado="pendiente",
        )
        assert tarea.id is not None


class TestCmsModels:
    """TestCmsModels."""

    def test_articulo_creation(self, db):
        """test_articulo_creation."""
        from apps.cms.models import Articulo
        from tests.helpers import create_test_agencia

        agencia = create_test_agencia()
        articulo = Articulo.objects.create(
            agencia=agencia,
            titulo="Test Article",
            slug="test-article",
            contenido="Test content",
            estado="BOR",
        )
        assert articulo.id is not None


class TestCrmModels:
    """TestCrmModels."""

    def test_cliente_creation(self, db):
        """test_cliente_creation."""
        from tests.helpers import create_test_cliente

        cliente = create_test_cliente()
        assert cliente.id is not None
        assert cliente.nombres == "Juan"

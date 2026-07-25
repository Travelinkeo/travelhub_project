"""Tests para modelos de apps restantes: cotizaciones, crm, gamification, marketing, reports, tasks, cms."""

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.models]


class TestCotizacionesModels:
    """Test Cotizaciones Models."""
    def test_cotizacion_creation(self, db):
        """Cotizacion creation."""
        from apps.cotizaciones.models import Cotizacion
        from tests.helpers import create_test_agencia, create_test_cliente, create_test_moneda

        agencia = create_test_agencia()
        cliente = create_test_cliente()
        moneda = create_test_moneda()
        cotizacion = Cotizacion.objects.create(
            agencia=agencia,
            cliente=cliente,
            moneda=moneda,
            tipo_viaje="NAC",
            estado="PEN",
        )
        assert cotizacion.id is not None
        assert str(cotizacion) is not None


class TestGamificationModels:
    """Test Gamification Models."""
    def test_puntaje_creation(self, db):
        """Puntaje creation."""
        from apps.gamification.models import Puntaje
        from tests.helpers import create_test_user

        usuario = create_test_user()
        puntaje = Puntaje.objects.create(
            usuario=usuario,
            puntos=100,
            razon="Test",
        )
        assert puntaje.id is not None

    def test_logro_creation(self, db):
        """Logro creation."""
        from apps.gamification.models import Logro

        logro = Logro.objects.create(
            nombre="Test Achievement",
            descripcion="Test description",
            icono="🏆",
        )
        assert logro.id is not None


class TestMarketingModels:
    """Test Marketing Models."""
    def test_campania_creation(self, db):
        """Campania creation."""
        from apps.marketing.models import Campania
        from tests.helpers import create_test_agencia

        agencia = create_test_agencia()
        campania = Campania.objects.create(
            agencia=agencia,
            nombre="Test Campaign",
            tipo="EMAIL",
            estado="BORRADOR",
        )
        assert campania.id is not None


class TestReportsModels:
    """Test Reports Models."""
    def test_reporte_programado_creation(self, db):
        """Reporte programado creation."""
        from apps.reports.models import ReporteProgramado
        from tests.helpers import create_test_agencia

        agencia = create_test_agencia()
        reporte = ReporteProgramado.objects.create(
            agencia=agencia,
            nombre="Test Report",
            tipo_reporte="VENTAS",
            frecuencia="DIARIO",
            formato="PDF",
            activo=True,
        )
        assert reporte.id is not None


class TestTasksModels:
    """Test Tasks Models."""
    def test_tarea_creation(self, db):
        """Tarea creation."""
        from apps.tasks.models import Tarea
        from tests.helpers import create_test_agencia, create_test_user

        agencia = create_test_agencia()
        usuario = create_test_user()
        tarea = Tarea.objects.create(
            agencia=agencia,
            titulo="Test Task",
            descripcion="Test",
            asignado_a=usuario,
            prioridad="MEDIA",
            estado="PEN",
        )
        assert tarea.id is not None


class TestCmsModels:
    """Test Cms Models."""
    def test_articulo_creation(self, db):
        """Articulo creation."""
        from apps.cms.models import Articulo
        from tests.helpers import create_test_user

        autor = create_test_user()
        articulo = Articulo.objects.create(
            titulo="Test Article",
            contenido="Test content",
            autor=autor,
            estado="BORRADOR",
        )
        assert articulo.id is not None


class TestCrmModels:
    """Test Crm Models."""
    def test_cliente_creation(self, db):
        """Cliente creation."""
        from apps.crm.models import Cliente
        from tests.helpers import create_test_cliente

        cliente = create_test_cliente()
        assert cliente.id is not None
        assert cliente.nombres == "Juan"

"""Tests para vistas y APIs de reconciliación"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.bookings.models import BoletoImportado
from apps.finance.models.reconciliacion import (
    ConciliacionBoleto,
    LineaReporteReconciliacion,
    ReporteReconciliacion,
)
from core.models import Agencia, UsuarioAgencia

User = get_user_model()


@pytest.mark.django_db
class TestReportListView:
    """Tests para ReportListView (reconciliacion_dashboard_htmx)"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.client = Client()
        self.agencia = Agencia.objects.create(nombre="Test Agency")
        self.user = User.objects.create_user(
            username="testuser1", email="test@agency.com", password="testpass123", is_staff=True
        )
        self.user.agencia = self.agencia
        self.user.save()
        UsuarioAgencia.objects.create(usuario=self.user, agencia=self.agencia, rol="admin", activo=True)

    def test_list_view_requires_login(self):
        response = self.client.get(reverse("finance:reconciliacion_dashboard_htmx"))
        assert response.status_code in [302, 401, 403]

    def test_list_view_returns_reports(self):
        self.client.force_login(self.user)

        ReporteReconciliacion.objects.create(
            agencia=self.agencia, proveedor="KIU", estado="PROCESADO"
        )
        ReporteReconciliacion.objects.create(
            agencia=self.agencia, proveedor="BSP", estado="PENDIENTE"
        )

        response = self.client.get(reverse("finance:reconciliacion_dashboard_htmx"))
        assert response.status_code == 200
        assert "ultimos_reportes" in response.context

    def test_list_view_shows_stats(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("finance:reconciliacion_dashboard_htmx"))
        assert response.status_code == 200
        assert "stats_globales" in response.context


@pytest.mark.django_db
class TestReconciliationDetailView:
    """Tests para ReporteReconciliacionDetailView"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.client = Client()
        self.agencia = Agencia.objects.create(nombre="Test Agency")
        self.user = User.objects.create_user(
            username="testuser2", email="test@agency.com", password="testpass123", is_staff=True
        )
        self.user.agencia = self.agencia
        self.user.save()
        UsuarioAgencia.objects.create(usuario=self.user, agencia=self.agencia, rol="admin", activo=True)

        self.reporte = ReporteReconciliacion.objects.create(
            agencia=self.agencia, proveedor="KIU", estado="CON_DISCREPANCIAS"
        )

        self.linea1 = LineaReporteReconciliacion.objects.create(
            reporte=self.reporte,
            agencia=self.agencia,
            numero_boleto_reportado="7258019382",
            tarifa_base_cobrada=Decimal("100.00"),
            impuestos_cobrados=Decimal("20.00"),
            total_cobrado=Decimal("120.00"),
        )

        self.boleto1 = BoletoImportado.objects.create(
            agencia=self.agencia, numero_boleto="7258019382", total_boleto=Decimal("115.00")
        )

        self.conciliacion_ok = ConciliacionBoleto.objects.create(
            reporte=self.reporte,
            agencia=self.agencia,
            linea_reporte=self.linea1,
            boleto_local=self.boleto1,
            estado="OK",
            diferencia_total=Decimal("5.00"),
        )

    def test_detail_view_requires_login(self):
        response = self.client.get(
            reverse("finance:reconciliacion_detail", kwargs={"pk": self.reporte.pk})
        )
        assert response.status_code in [302, 401, 403]

    def test_detail_view_returns_context(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("finance:reconciliacion_detail", kwargs={"pk": self.reporte.pk})
        )
        assert response.status_code == 200
        assert "reporte" in response.context
        assert "conciliaciones_lines" in response.context

    def test_detail_view_conciliaciones_count(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("finance:reconciliacion_detail", kwargs={"pk": self.reporte.pk})
        )
        assert response.context["conciliaciones_lines"].count() == 1


@pytest.mark.django_db
class TestReporteReconciliacionModel:
    """Tests para el modelo ReporteReconciliacion"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.agencia = Agencia.objects.create(nombre="Test Agency")
        self.reporte = ReporteReconciliacion.objects.create(
            agencia=self.agencia, proveedor="KIU", estado="PROCESADO"
        )

    def test_discrepancias_count_property(self):
        ConciliacionBoleto.objects.create(
            reporte=self.reporte,
            agencia=self.agencia,
            estado="OK",
            diferencia_total=Decimal("0.00"),
        )
        ConciliacionBoleto.objects.create(
            reporte=self.reporte,
            agencia=self.agencia,
            estado="DISCREPANCIA",
            diferencia_total=Decimal("10.00"),
        )
        ConciliacionBoleto.objects.create(
            reporte=self.reporte,
            agencia=self.agencia,
            estado="DISCREPANCIA",
            diferencia_total=Decimal("5.00"),
        )

        assert self.reporte.discrepancias_count == 2

    def test_discrepancias_count_zero(self):
        ConciliacionBoleto.objects.create(
            reporte=self.reporte,
            agencia=self.agencia,
            estado="OK",
            diferencia_total=Decimal("0.00"),
        )

        assert self.reporte.discrepancias_count == 0

    def test_string_representation(self):
        expected = f"Reporte KIU - {self.reporte.fecha_subida.strftime('%d/%m/%Y')} (Test Agency)"
        assert str(self.reporte) == expected


@pytest.mark.django_db
class TestConciliacionBoletoModel:
    """Tests para el modelo ConciliacionBoleto"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.agencia = Agencia.objects.create(nombre="Test Agency")
        self.reporte = ReporteReconciliacion.objects.create(
            agencia=self.agencia, proveedor="KIU", estado="PROCESADO"
        )

    def test_estado_choices(self):
        conciliacion = ConciliacionBoleto.objects.create(
            reporte=self.reporte,
            agencia=self.agencia,
            estado="OK",
            diferencia_total=Decimal("0.00"),
        )
        assert conciliacion.estado == "OK"

    def test_string_representation(self):
        conciliacion = ConciliacionBoleto.objects.create(
            reporte=self.reporte,
            agencia=self.agencia,
            estado="DISCREPANCIA",
            diferencia_total=Decimal("15.50"),
        )
        assert "DISCREPANCIA" in str(conciliacion)
        assert "15.50" in str(conciliacion)


@pytest.mark.django_db
class TestLineaReporteReconciliacionModel:
    """Tests para el modelo LineaReporteReconciliacion"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.agencia = Agencia.objects.create(nombre="Test Agency")
        self.reporte = ReporteReconciliacion.objects.create(
            agencia=self.agencia, proveedor="KIU", estado="PROCESADO"
        )

    def test_string_representation(self):
        linea = LineaReporteReconciliacion.objects.create(
            reporte=self.reporte,
            agencia=self.agencia,
            numero_boleto_reportado="7258019382",
            total_cobrado=Decimal("150.00"),
        )
        assert "7258019382" in str(linea)
        assert "150.00" in str(linea)


from unittest.mock import patch

@pytest.mark.django_db(transaction=True)
class TestReconciliationAsync:
    """Tests para los flujos asíncronos de conciliación y sus vistas"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.client = Client()
        self.agencia = Agencia.objects.create(nombre="Test Agency")
        self.user = User.objects.create_user(
            username="testuser_async", email="test@agency.com", password="testpass123", is_staff=True
        )
        self.user.agencia = self.agencia
        self.user.save()
        UsuarioAgencia.objects.create(usuario=self.user, agencia=self.agencia, rol="admin", activo=True)
        self.client.force_login(self.user)

        self.reporte = ReporteReconciliacion.objects.create(
            agencia=self.agencia, proveedor="KIU", estado="PENDIENTE"
        )

    @patch("apps.finance.tasks_reconciliation.conciliar_reporte_batch_task.delay")
    def test_process_reconciliacion_htmx_view_starts_task(self, mock_delay):
        response = self.client.get(
            reverse("finance:reconciliacion_process", kwargs={"pk": self.reporte.pk})
        )
        # Debería redirigir al detalle
        assert response.status_code == 302
        assert response.url == reverse("finance:reconciliacion_detail", kwargs={"pk": self.reporte.pk})

        # El estado debería ser PROCESANDO
        self.reporte.refresh_from_db()
        assert self.reporte.estado == "PROCESANDO"

        # Debería haber encolado el task de Celery con los argumentos correctos
        mock_delay.assert_called_once_with(
            reporte_id=str(self.reporte.pk),
            agencia_id=self.agencia.pk
        )


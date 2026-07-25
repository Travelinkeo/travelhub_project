"""Tests para Reports."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.reports.models import KpiSnapshot, ReporteKPI, ReporteProgramado
from core.models.agencia import Agencia


class ReporteKPIModelTest(TestCase):
    """Reporte Kpimodel Test."""
    def setUp(self):
        """SetUp."""
        self.agencia = Agencia.objects.create(nombre="Report Agency")
        self.reporte = ReporteKPI.objects.create(
            nombre="Ventas Mensuales",
            tipo="ventas",
            periodo="mensual",
            agencia=self.agencia,
        )

    def test_str(self):
        """Str."""
        self.assertEqual(str(self.reporte), "Ventas Mensuales")

    def test_defaults(self):
        """Defaults."""
        self.assertTrue(self.reporte.activo)
        self.assertEqual(self.reporte.tipo, "ventas")
        self.assertEqual(self.reporte.periodo, "mensual")

    def test_tipos_disponibles(self):
        """Tipos disponibles."""
        tipos = dict(ReporteKPI.TIPOS)
        self.assertIn("ventas", tipos)
        self.assertIn("rentabilidad", tipos)
        self.assertIn("general", tipos)

    def test_periodos_disponibles(self):
        """Periodos disponibles."""
        periodos = dict(ReporteKPI.PERIODOS)
        self.assertIn("diario", periodos)
        self.assertIn("anual", periodos)


class KpiSnapshotModelTest(TestCase):
    """Kpi Snapshot Model Test."""
    def setUp(self):
        """Setup."""
        self.agencia = Agencia.objects.create(nombre="Snapshot Agency")
        self.snap = KpiSnapshot.objects.create(
            agencia=self.agencia,
            metrica="ventas_totales",
            valor=42.00,
            fecha=date.today(),
        )

    def test_str(self):
        """Str."""
        self.assertIn("Ventas Totales", str(self.snap))

    def test_unique_together(self):
        """Unique together."""
        with self.assertRaises(Exception):
            KpiSnapshot.objects.create(
                agencia=self.agencia,
                metrica="ventas_totales",
                valor=10,
                fecha=date.today(),
            )

    def test_diferente_fecha_permitida(self):
        """Diferente fecha permitida."""
        snap2 = KpiSnapshot.objects.create(
            agencia=self.agencia,
            metrica="ventas_totales",
            valor=99,
            fecha=date(2024, 1, 1),
        )
        self.assertEqual(snap2.valor, 99)

    def test_ordering(self):
        """Ordering."""
        older = KpiSnapshot.objects.create(
            agencia=self.agencia,
            metrica="clientes_nuevos",
            valor=5,
            fecha=date(2024, 1, 1),
        )
        newer = KpiSnapshot.objects.create(
            agencia=self.agencia,
            metrica="clientes_nuevos",
            valor=10,
            fecha=date(2024, 6, 1),
        )
        snaps = list(KpiSnapshot.objects.filter(agencia=self.agencia, metrica="clientes_nuevos"))
        self.assertEqual(snaps[0], newer)
        self.assertEqual(snaps[1], older)


class ReporteProgramadoModelTest(TestCase):
    """Reporte Programado Model Test."""
    def setUp(self):
        """Setup."""
        self.agencia = Agencia.objects.create(nombre="Scheduled Agency")
        self.rp = ReporteProgramado.objects.create(
            nombre="Reporte Semanal",
            tipo="general",
            frecuencia="semanal",
            dia_semana=1,
            agencia=self.agencia,
            destinatarios=["admin@test.com", "ventas@test.com"],
        )

    def test_str(self):
        """Str."""
        self.assertIn("Reporte Semanal", str(self.rp))

    def test_defaults(self):
        """Defaults."""
        self.assertTrue(self.rp.activo)
        self.assertIsNone(self.rp.ultimo_envio)

    def test_destinatarios_json(self):
        """Destinatarios json."""
        self.assertEqual(len(self.rp.destinatarios), 2)
        self.assertIn("admin@test.com", self.rp.destinatarios)

    def test_sin_destinatarios(self):
        """Sin destinatarios."""
        rp2 = ReporteProgramado.objects.create(
            nombre="Sin Destinatarios", tipo="ventas", frecuencia="mensual", agencia=self.agencia
        )
        self.assertEqual(rp2.destinatarios, [])


class ReportsViewsTest(TestCase):
    """Reports Views Test."""
    def setUp(self):
        """Setup."""
        self.user = get_user_model().objects.create_user(
            username="reports_view", password="pass1234"
        )
        self.agencia = Agencia.objects.create(nombre="Reports Agency")
        self.client.login(username="reports_view", password="pass1234")

    def test_kpi_dashboard_requires_login(self):
        """Kpi dashboard requires login."""
        self.client.logout()
        response = self.client.get(reverse("reports:kpi_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_kpi_dashboard_renders(self):
        """Kpi dashboard renders."""
        response = self.client.get(reverse("reports:kpi_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_chart_data_returns_json(self):
        """Chart data returns json."""
        response = self.client.get(reverse("reports:kpi_chart_data"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response["Content-Type"])

    def test_chart_data_invalid_chart(self):
        """Chart data invalid chart."""
        response = self.client.get(
            reverse("reports:kpi_chart_data"), {"chart": "invalid"}
        )
        self.assertEqual(response.status_code, 200)

    def test_export_csv(self):
        """Export csv."""
        response = self.client.get(reverse("reports:kpi_export"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("Content-Disposition", response)

    def test_export_csv_contains_headers(self):
        """Export csv contains headers."""
        response = self.client.get(reverse("reports:kpi_export"))
        content = response.content.decode("utf-8")
        self.assertIn("Métrica", content)
        self.assertIn("Valor", content)


class ReportsKPIMetricsServiceTest(TestCase):
    """Reports Kpimetrics Service Test."""
    def setUp(self):
        """Setup."""
        self.agencia = Agencia.objects.create(nombre="KPI Agency")
        self.user = get_user_model().objects.create_user(username="kpi_user")

    def test_kpi_metrics_resumen_structure(self):
        """Kpi metrics resumen structure."""
        from apps.reports.services.kpi_metrics import KPIMetrics

        metrics = KPIMetrics(self.agencia)
        resumen = metrics.resumen()
        expected_keys = [
            "total_ventas", "monto_total", "ticket_promedio",
            "utilidad", "margen_bruto", "clientes",
            "boletos", "comisiones_pendientes", "comisiones_liquidadas",
        ]
        for key in expected_keys:
            self.assertIn(key, resumen)

    def test_ventas_por_dia_empty(self):
        """Ventas por dia empty."""
        from apps.reports.services.kpi_metrics import KPIMetrics

        metrics = KPIMetrics(self.agencia)
        data = metrics.ventas_por_dia(30)
        self.assertEqual(data, {})

    def test_ticket_promedio_zero_when_no_sales(self):
        """Ticket promedio zero when no sales."""
        from apps.reports.services.kpi_metrics import KPIMetrics

        metrics = KPIMetrics(self.agencia)
        self.assertEqual(metrics.ticket_promedio(), 0)

    def test_margen_bruto_zero_when_no_sales(self):
        """Margen bruto zero when no sales."""
        from apps.reports.services.kpi_metrics import KPIMetrics

        metrics = KPIMetrics(self.agencia)
        utilidad, margen = metrics.margen_bruto()
        self.assertEqual(utilidad, 0)
        self.assertEqual(margen, 0)

    def test_clientes_nuevos_zero(self):
        """Clientes nuevos zero."""
        from apps.reports.services.kpi_metrics import KPIMetrics

        metrics = KPIMetrics(self.agencia)
        self.assertEqual(metrics.clientes_nuevos(30), 0)

    def test_boletos_por_aerolinea_empty(self):
        """Boletos por aerolinea empty."""
        from apps.reports.services.kpi_metrics import KPIMetrics

        metrics = KPIMetrics(self.agencia)
        self.assertEqual(metrics.boletos_por_aerolinea(), {})


class ReportsChartDataServiceTest(TestCase):
    """Reports Chart Data Service Test."""
    def setUp(self):
        """Setup."""
        self.agencia = Agencia.objects.create(nombre="Chart Agency")

    def test_resumen_cards_structure(self):
        """Resumen cards structure."""
        from apps.reports.services.kpi_metrics import KPIMetrics
        from apps.reports.services.chart_data import resumen_cards

        metrics = KPIMetrics(self.agencia)
        cards = resumen_cards(metrics)
        self.assertIsInstance(cards, list)

    def test_ventas_diarias_chart_structure(self):
        """Ventas diarias chart structure."""
        from apps.reports.services.kpi_metrics import KPIMetrics
        from apps.reports.services.chart_data import ventas_diarias_chart

        metrics = KPIMetrics(self.agencia)
        chart = ventas_diarias_chart(metrics)
        self.assertIn("labels", chart)
        self.assertIn("datasets", chart)

    def test_boletos_por_aerolinea_chart(self):
        """Boletos por aerolinea chart."""
        from apps.reports.services.kpi_metrics import KPIMetrics
        from apps.reports.services.chart_data import boletos_por_aerolinea_chart

        metrics = KPIMetrics(self.agencia)
        chart = boletos_por_aerolinea_chart(metrics)
        self.assertIn("labels", chart)
        self.assertIn("datasets", chart)

    def test_ventas_por_vendedor_chart(self):
        """Ventas por vendedor chart."""
        from apps.reports.services.kpi_metrics import KPIMetrics
        from apps.reports.services.chart_data import ventas_por_vendedor_chart

        metrics = KPIMetrics(self.agencia)
        chart = ventas_por_vendedor_chart(metrics)
        self.assertIn("labels", chart)
        self.assertIn("datasets", chart)


class ReportsExporterServiceTest(TestCase):
    """Reports Exporter Service Test."""
    def setUp(self):
        """Setup."""
        self.agencia = Agencia.objects.create(nombre="Export Agency")

    def test_exportar_csv_generates_content(self):
        """Exportar csv generates content."""
        from apps.reports.services.kpi_metrics import KPIMetrics
        from apps.reports.services.report_exporter import exportar_csv

        metrics = KPIMetrics(self.agencia)
        csv_content = exportar_csv(metrics)
        self.assertIn("Métrica", csv_content)
        self.assertIn("Valor", csv_content)
        self.assertIn("Total Ventas", csv_content)

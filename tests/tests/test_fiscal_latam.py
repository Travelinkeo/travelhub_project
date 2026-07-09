from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.finance.models.core_finance import Factura
from apps.finance.models.currencies import Moneda
from apps.finance.models.facturas_proveedores import FacturaProveedor
from apps.finance.models.retenciones import RetencionISLR
from core.models import Agencia

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestFiscalLatam:
    """
    Suite de pruebas para el cumplimiento fiscal LatAm (Libro de Compras, Ventas e ISLR XML).
    """

    @pytest.fixture(autouse=True)
    def setup_data(self):
        # 1. Crear Agencia
        self.agencia = Agencia.objects.create(nombre="Test Fiscal Agency", rif="J123456789")

        # 2. Crear Moneda
        self.moneda = Moneda.objects.create(codigo_iso="VES", nombre="Bolívares", simbolo="Bs")

        # 3. Crear Usuario Administrador
        from core.models import UsuarioAgencia

        self.user = User.objects.create_user(
            username="fiscal_admin", email="admin@fiscal.com", password="password123"
        )
        self.usuario_agencia = UsuarioAgencia.objects.create(
            usuario=self.user, agencia=self.agencia, activo=True, rol="admin"
        )
        self.user.agencia = self.agencia
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # 4. Crear Facturas de Proveedores (para Libro de Compras)
        self.factura_prov = FacturaProveedor.objects.create(
            agencia=self.agencia,
            proveedor_nombre="AEROLINEAS ESTELAR",
            numero_factura="FAC-PROV-001",
            monto_total=Decimal("116.00"),
            moneda=self.moneda,
            fecha_emision=date(2026, 7, 9),
            estado=FacturaProveedor.EstadoFactura.CONCILIADA,
            datos_json={"base_gravada": "100.00", "iva": "16.00", "proveedor_rif": "J-99999999-9"},
        )

        # 5. Crear Factura Cliente y Retención ISLR (para XML)
        self.factura_cli = Factura.objects.create(
            agencia=self.agencia,
            moneda=self.moneda,
            numero_factura="FAC-CLI-001",
            numero_control="CTRL-001",
            cliente_identificacion="J-88888888-8",
            monto_total=Decimal("500.00"),
        )
        self.retencion = RetencionISLR.objects.create(
            agencia=self.agencia,
            numero_comprobante="COMP-202607-001",
            factura=self.factura_cli,
            fecha_emision=date(2026, 7, 9),
            fecha_operacion=date(2026, 7, 9),
            periodo_fiscal="2026-07",
            tipo_operacion=RetencionISLR.TipoOperacion.COMISIONES_MERCANTILES,
            codigo_concepto="03-04",
            base_imponible=Decimal("500.00"),
            porcentaje_retencion=Decimal("5.00"),
            monto_retenido=Decimal("25.00"),
            estado=RetencionISLR.Estado.APLICADA,
        )

    def test_libro_compras_generation_json_and_csv(self):
        """
        Verifica la generación del Libro de Compras en formato JSON y CSV/Excel.
        """
        url = reverse("finance:libro-compras-generar")

        # Test JSON
        response = self.client.get(
            url, {"fecha_inicio": "2026-07-01", "fecha_fin": "2026-07-31", "formato": "json"}
        )
        assert response.status_code == 200
        data = response.json()

        assert data["resumen"]["total_facturas"] == 1
        assert float(data["totales"]["total"]) == 116.00
        assert float(data["totales"]["base_gravada"]) == 100.00
        assert float(data["totales"]["iva_16"]) == 16.00
        assert data["compras"][0]["proveedor_nombre"] == "AEROLINEAS ESTELAR"
        assert data["compras"][0]["proveedor_rif"] == "J-99999999-9"

        # Test CSV
        response_csv = self.client.get(
            url, {"fecha_inicio": "2026-07-01", "fecha_fin": "2026-07-31", "formato": "csv"}
        )
        assert response_csv.status_code == 200
        assert response_csv["Content-Type"] == "text/csv; charset=utf-8"
        assert b"FAC-PROV-001" in response_csv.content
        assert b"AEROLINEAS ESTELAR" in response_csv.content
        assert (
            b"100.00;16.00" in response_csv.content or b"100.00;0.00;16.00" in response_csv.content
        )

    def test_retenciones_islr_xml_generation(self):
        """
        Verifica la exportación del archivo XML de retenciones ISLR formateado para el portal del SENIAT.
        """
        url = reverse("finance:retenciones-xml-descargar-xml")
        response = self.client.get(url, {"fecha_inicio": "2026-07-01", "fecha_fin": "2026-07-31"})

        assert response.status_code == 200
        assert response["Content-Type"] == "application/xml; charset=utf-8"
        xml_content = response.content.decode("utf-8")

        # Verificar cabecera del agente y período
        assert 'RifAgente="J123456789"' in xml_content
        assert 'Periodo="202607"' in xml_content

        # Verificar detalles de la retención
        assert (
            "<RifRetenido>J888888888</RifRetenido>" in xml_content
        )  # RIF sanitizado (sin guiones)
        assert "<NumeroFactura>FAC-CLI-001</NumeroFactura>" in xml_content
        assert "<NumeroControl>CTRL-001</NumeroControl>" in xml_content
        assert "<CodigoConcepto>03-04</CodigoConcepto>" in xml_content
        assert "<MontoOperacion>500.00</MontoOperacion>" in xml_content
        assert "<PorcentajeRetencion>5.00</PorcentajeRetencion>" in xml_content

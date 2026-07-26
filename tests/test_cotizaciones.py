import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.cotizaciones.models import Cotizacion, ItemCotizacion
from apps.cotizaciones.serializers import CotizacionSerializer

pytestmark = pytest.mark.django_db


@pytest.mark.django_db
class TestCotizacionModel:
    """TestCotizacionModel."""

    def test_crear_cotizacion_con_numero_auto(self, agencia_premium, moneda_usd):
        """test_crear_cotizacion_con_numero_auto."""
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        assert cotizacion.numero_cotizacion.startswith("COT")
        assert cotizacion.numero_cotizacion.endswith("-0001")
        assert cotizacion.pk is not None

    def test_crear_cotizacion_con_prefijo_agencia(self, agencia_premium, moneda_usd):
        """test_crear_cotizacion_con_prefijo_agencia."""
        slug = agencia_premium.subdominio_slug.upper()
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        assert slug in cotizacion.numero_cotizacion

    def test_str_representation(self, agencia_premium, moneda_usd):
        """test_str_representation."""
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        assert str(cotizacion) == cotizacion.numero_cotizacion

    def test_str_fallback_sin_numero(self):
        """test_str_fallback_sin_numero."""
        cotizacion = Cotizacion()
        assert hasattr(cotizacion, "numero_cotizacion")

    def test_calcular_total_con_items(self, agencia_premium, moneda_usd):
        """test_calcular_total_con_items."""
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        ItemCotizacion.objects.create(
            cotizacion=cotizacion,
            agencia=agencia_premium,
            tipo_item="VUE",
            descripcion="Vuelo Miami",
            cantidad=1,
            precio_unitario=Decimal("500.00"),
            costo=Decimal("500.00"),
        )
        ItemCotizacion.objects.create(
            cotizacion=cotizacion,
            agencia=agencia_premium,
            tipo_item="ALO",
            descripcion="Hotel 3 noches",
            cantidad=3,
            precio_unitario=Decimal("150.00"),
            costo=Decimal("450.00"),
        )
        cotizacion.calcular_total()
        cotizacion.refresh_from_db()
        assert cotizacion.total_cotizado == Decimal("950.00")

    def test_calcular_total_sin_items(self, agencia_premium, moneda_usd):
        """test_calcular_total_sin_items."""
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        cotizacion.calcular_total()
        cotizacion.refresh_from_db()
        assert cotizacion.total_cotizado == Decimal("0.00")

    def test_convertir_a_venta_aceptada(self, agencia_premium, moneda_usd, db):
        """test_convertir_a_venta_aceptada."""
        from apps.bookings.models import Venta
        from apps.crm.models import Cliente

        cli = Cliente.objects.create(agencia=agencia_premium, nombres="Test")
        real_venta = Venta.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            cliente=cli,
            total_venta=Decimal("500.00"),
            saldo_pendiente=Decimal("500.00"),
        )
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            destino="Miami",
            estado=Cotizacion.EstadoCotizacion.ACEPTADA,
            total_cotizado=Decimal("500.00"),
        )
        with patch("apps.bookings.models.Venta.objects.create", return_value=real_venta):
            venta = cotizacion.convertir_a_venta()
        assert venta is not None
        cotizacion.refresh_from_db()
        assert cotizacion.estado == Cotizacion.EstadoCotizacion.CONVERTIDA

    def test_convertir_a_venta_rechazada_raise(self, agencia_premium, moneda_usd):
        """test_convertir_a_venta_rechazada_raise."""
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            destino="Miami",
            estado=Cotizacion.EstadoCotizacion.RECHAZADA,
        )
        with pytest.raises(ValueError, match="aceptadas"):
            cotizacion.convertir_a_venta()

    def test_convertir_a_venta_borrador_raise(self, agencia_premium, moneda_usd):
        """test_convertir_a_venta_borrador_raise."""
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            destino="Miami",
            estado=Cotizacion.EstadoCotizacion.BORRADOR,
        )
        with pytest.raises(ValueError, match="aceptadas"):
            cotizacion.convertir_a_venta()

    def test_get_whatsapp_link_con_cliente(self, agencia_premium, moneda_usd, db):
        """test_get_whatsapp_link_con_cliente."""
        from apps.crm.models import Cliente

        cli = Cliente.objects.create(
            agencia=agencia_premium, nombres="Juan", telefono_principal="+584141234567"
        )
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            destino="Miami",
            cliente=cli,
            total_cotizado=Decimal("500.00"),
        )
        link = cotizacion.get_whatsapp_link()
        assert "wa.me" in link
        assert "Miami" in link
        assert "text=" in link

    def test_get_whatsapp_link_sin_cliente(self, agencia_premium, moneda_usd):
        """test_get_whatsapp_link_sin_cliente."""
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            destino="Miami",
            nombre_cliente_manual="Juan Pérez",
            total_cotizado=Decimal("500.00"),
        )
        link = cotizacion.get_whatsapp_link()
        assert "wa.me" in link


@pytest.mark.django_db
class TestItemCotizacionModel:
    """TestItemCotizacionModel."""

    def test_crear_item(self, agencia_premium, moneda_usd):
        """test_crear_item."""
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        item = ItemCotizacion.objects.create(
            cotizacion=cotizacion,
            agencia=agencia_premium,
            tipo_item="VUE",
            descripcion="Vuelo directo",
            cantidad=1,
            precio_unitario=Decimal("300.00"),
            costo=Decimal("300.00"),
        )
        assert item.pk is not None
        assert str(item) == "Vuelo - Vuelo directo"

    def test_item_enum_values(self):
        """test_item_enum_values."""
        assert ItemCotizacion.TipoItem.VUELO == "VUE"
        assert ItemCotizacion.TipoItem.ALOJAMIENTO == "ALO"
        assert ItemCotizacion.TipoItem.ACTIVIDAD == "ACT"

    def test_item_default_tipo(self):
        """test_item_default_tipo."""
        item = ItemCotizacion(tipo_item=ItemCotizacion.TipoItem.OTRO)
        assert item.get_tipo_item_display() == "Otro"

    def test_item_str(self, agencia_premium, moneda_usd):
        """test_item_str."""
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        item = ItemCotizacion.objects.create(
            cotizacion=cotizacion,
            agencia=agencia_premium,
            descripcion="Hotel",
            costo=Decimal("100.00"),
        )
        assert "Hotel" in str(item)

    def test_item_soft_delete(self, agencia_premium, moneda_usd):
        """test_item_soft_delete."""
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        item = ItemCotizacion.objects.create(
            cotizacion=cotizacion,
            agencia=agencia_premium,
            descripcion="Item",
            costo=Decimal("100.00"),
        )
        item.delete()
        item.refresh_from_db()
        assert item.is_deleted is True
        assert item.deleted_at is not None


@pytest.mark.django_db
class TestCotizacionSerializer:
    """TestCotizacionSerializer."""

    def test_serializer_contains_expected_fields(self, agencia_premium, moneda_usd):
        """test_serializer_contains_expected_fields."""
        from datetime import date

        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            destino="Miami",
            fecha_emision=date.today(),
            fecha_vencimiento=date.today(),
        )
        serializer = CotizacionSerializer(cotizacion)
        data = serializer.data
        assert "id_cotizacion" in data
        assert "uuid" in data
        assert "numero_cotizacion" in data
        assert "destino" in data
        assert "total_cotizado" in data
        assert "estado" in data

    def test_serializer_read_only_fields(self, agencia_premium, moneda_usd):
        """test_serializer_read_only_fields."""
        data = {
            "agencia": agencia_premium.id,
            "uuid": str(uuid.uuid4()),
            "numero_cotizacion": "CUSTOM-123",
            "destino": "Miami",
        }
        serializer = CotizacionSerializer(data=data)
        assert serializer.is_valid() is True
        assert "agencia" not in serializer.validated_data
        assert "uuid" not in serializer.validated_data
        assert "numero_cotizacion" not in serializer.validated_data
        assert "destino" in serializer.validated_data


@pytest.mark.django_db
class TestCotizacionAPI:
    """TestCotizacionAPI."""

    def _setup_user_agencia(self, usuario_staff, agencia):
        """_setup_user_agencia."""
        from core.api import UsuarioAgencia

        UsuarioAgencia.objects.get_or_create(
            usuario=usuario_staff, agencia=agencia, defaults={"rol": "admin"}
        )

    def test_list_cotizaciones_authenticated(self, agencia_premium, moneda_usd, usuario_staff):
        """test_list_cotizaciones_authenticated."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        Cotizacion.objects.create(agencia=agencia_premium, moneda=moneda_usd, destino="Miami")
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.get("/cotizaciones/api/cotizaciones/")
        assert response.status_code == status.HTTP_200_OK

    def test_list_cotizaciones_unauthenticated(self):
        """test_list_cotizaciones_unauthenticated."""
        client = APIClient()
        response = client.get("/cotizaciones/api/cotizaciones/")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_create_cotizacion_authenticated(self, agencia_premium, moneda_usd, usuario_staff):
        """test_create_cotizacion_authenticated."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        from datetime import date

        response = client.post(
            "/cotizaciones/api/cotizaciones/",
            {
                "moneda": moneda_usd.pk,
                "destino": "Miami",
                "numero_pasajeros": 2,
                "fecha_emision": date.today().isoformat(),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["destino"] == "Miami"
        assert response.data["numero_cotizacion"].startswith("COT")

    def test_retrieve_cotizacion(self, agencia_premium, moneda_usd, usuario_staff):
        """test_retrieve_cotizacion."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.get(f"/cotizaciones/api/cotizaciones/{cotizacion.id_cotizacion}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["destino"] == "Miami"

    def test_convertir_a_venta_aceptada(self, agencia_premium, moneda_usd, usuario_staff, db):
        """test_convertir_a_venta_aceptada."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        from apps.bookings.models import Venta
        from apps.crm.models import Cliente

        cli = Cliente.objects.create(agencia=agencia_premium, nombres="Test")
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            destino="Miami",
            estado=Cotizacion.EstadoCotizacion.ACEPTADA,
            total_cotizado=Decimal("500.00"),
        )
        real_venta = Venta.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            cliente=cli,
            total_venta=Decimal("500.00"),
            saldo_pendiente=Decimal("500.00"),
        )
        with patch.object(Cotizacion, "convertir_a_venta", return_value=real_venta):
            client = APIClient()
            client.force_authenticate(user=usuario_staff)
            response = client.post(
                f"/cotizaciones/api/cotizaciones/{cotizacion.id_cotizacion}/convertir_a_venta/"
            )
            assert response.status_code == status.HTTP_200_OK

    def test_convertir_a_venta_rechazada(self, agencia_premium, moneda_usd, usuario_staff):
        """test_convertir_a_venta_rechazada."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            destino="Miami",
            estado=Cotizacion.EstadoCotizacion.RECHAZADA,
        )
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.post(
            f"/cotizaciones/api/cotizaciones/{cotizacion.id_cotizacion}/convertir_a_venta/"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_marcar_enviada(self, agencia_premium, moneda_usd, usuario_staff):
        """test_marcar_enviada."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.post(
            f"/cotizaciones/api/cotizaciones/{cotizacion.id_cotizacion}/marcar_enviada/"
        )
        assert response.status_code == status.HTTP_200_OK
        cotizacion.refresh_from_db()
        assert cotizacion.estado == Cotizacion.EstadoCotizacion.ENVIADA

    def test_marcar_vista(self, agencia_premium, moneda_usd, usuario_staff):
        """test_marcar_vista."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            destino="Miami",
            estado=Cotizacion.EstadoCotizacion.ENVIADA,
        )
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.post(
            f"/cotizaciones/api/cotizaciones/{cotizacion.id_cotizacion}/marcar_vista/"
        )
        assert response.status_code == status.HTTP_200_OK
        cotizacion.refresh_from_db()
        assert cotizacion.estado == Cotizacion.EstadoCotizacion.VISTA

    def test_marcar_vista_sin_estado_previo(self, agencia_premium, moneda_usd, usuario_staff):
        """test_marcar_vista_sin_estado_previo."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            destino="Miami",
            estado=Cotizacion.EstadoCotizacion.BORRADOR,
        )
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.post(
            f"/cotizaciones/api/cotizaciones/{cotizacion.id_cotizacion}/marcar_vista/"
        )
        assert response.status_code == status.HTTP_200_OK
        cotizacion.refresh_from_db()
        assert cotizacion.estado == Cotizacion.EstadoCotizacion.BORRADOR

    def test_delete_cotizacion(self, agencia_premium, moneda_usd, usuario_staff):
        """test_delete_cotizacion."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.delete(f"/cotizaciones/api/cotizaciones/{cotizacion.id_cotizacion}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_create_cotizacion_sin_moneda(self, agencia_premium, usuario_staff):
        """test_create_cotizacion_sin_moneda."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        from datetime import date

        response = client.post(
            "/cotizaciones/api/cotizaciones/",
            {"destino": "Miami", "fecha_emision": date.today().isoformat()},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_cotizacion(self, agencia_premium, moneda_usd, usuario_staff):
        """test_update_cotizacion."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.patch(
            f"/cotizaciones/api/cotizaciones/{cotizacion.id_cotizacion}/",
            {"destino": "Cancún"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        cotizacion.refresh_from_db()
        assert cotizacion.destino == "Cancún"


@pytest.mark.django_db
class TestCotizacionMultiTenant:
    """TestCotizacionMultiTenant."""

    def _setup_user_agencia(self, usuario, agencia):
        """_setup_user_agencia."""
        from core.api import UsuarioAgencia

        UsuarioAgencia.objects.get_or_create(
            usuario=usuario, agencia=agencia, defaults={"rol": "admin"}
        )

    def test_no_accede_cotizacion_otra_agencia(
        self, agencia_premium, agencia_estandar, moneda_usd, usuario_staff
    ):
        """test_no_accede_cotizacion_otra_agencia."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        cotizacion_otra = Cotizacion.objects.create(
            agencia=agencia_estandar, moneda=moneda_usd, destino="Secreta"
        )
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.get(f"/cotizaciones/api/cotizaciones/{cotizacion_otra.id_cotizacion}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_solo_agencia_actual(
        self, agencia_premium, agencia_estandar, moneda_usd, usuario_staff
    ):
        """test_list_solo_agencia_actual."""
        self._setup_user_agencia(usuario_staff, agencia_premium)
        Cotizacion.objects.create(agencia=agencia_premium, moneda=moneda_usd, destino="Miami")
        Cotizacion.objects.create(agencia=agencia_estandar, moneda=moneda_usd, destino="Secreta")
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.get("/cotizaciones/api/cotizaciones/")
        assert response.status_code == status.HTTP_200_OK
        destinos = [c["destino"] for c in response.data["results"]]
        assert "Miami" in destinos
        assert "Secreta" not in destinos


class TestAiSchemas:
    """TestAiSchemas."""

    def test_flight_quote_segment_schema(self):
        """test_flight_quote_segment_schema."""
        from apps.cotizaciones.ai_schemas import FlightQuoteSegmentSchema

        seg = FlightQuoteSegmentSchema(
            airline="Avior",
            departureDate="20 Abr",
            departureCode="CCS",
            arrivalCode="MAD",
            departureCity="Caracas",
            arrivalCity="Madrid",
            departureTime="14:30",
            arrivalTime="17:00",
            stops="Directo",
        )
        assert seg.airline == "Avior"
        assert seg.stops == "Directo"
        assert seg.baggage == "1 Maleta 23kg"

    def test_cotizacion_magic_schema(self):
        """test_cotizacion_magic_schema."""
        from apps.cotizaciones.ai_schemas import CotizacionMagicSchema, FlightQuoteSegmentSchema

        esquema = CotizacionMagicSchema(
            destination="Madrid",
            destination_description="Descubre la magia de Madrid",
            type="Vuelo Redondo",
            outboundDate="15 Oct",
            returnDate="22 Oct",
            totalPrice=850.50,
            currency="USD",
            flights=[
                FlightQuoteSegmentSchema(
                    airline="Iberia",
                    departureDate="15 Oct",
                    departureCode="CCS",
                    arrivalCode="MAD",
                    departureCity="Caracas",
                    arrivalCity="Madrid",
                    departureTime="14:30",
                    arrivalTime="17:00",
                    stops="Directo",
                )
            ],
            image_search_query="Madrid Cityscape",
        )
        assert esquema.destination == "Madrid"
        assert esquema.totalPrice == 850.50
        assert len(esquema.flights) == 1
        assert esquema.flights[0].airline == "Iberia"

    def test_cotizacion_magic_schema_sin_retorno(self):
        """test_cotizacion_magic_schema_sin_retorno."""
        from apps.cotizaciones.ai_schemas import CotizacionMagicSchema, FlightQuoteSegmentSchema

        esquema = CotizacionMagicSchema(
            destination="Bogotá",
            destination_description="Visita Bogotá",
            type="Solo Ida",
            outboundDate="10 Jun",
            totalPrice=320.00,
            currency="USD",
            flights=[
                FlightQuoteSegmentSchema(
                    airline="Wingo",
                    departureDate="10 Jun",
                    departureCode="CCS",
                    arrivalCode="BOG",
                    departureCity="Caracas",
                    arrivalCity="Bogotá",
                    departureTime="08:00",
                    arrivalTime="09:30",
                    stops="Directo",
                )
            ],
            image_search_query="Bogota Skyline",
        )
        assert esquema.returnDate is None
        assert esquema.type == "Solo Ida"


class TestPdfService:
    """TestPdfService."""

    def test_generar_pdf_cotizacion_llama_renderer(self, agencia_premium, moneda_usd):
        """test_generar_pdf_cotizacion_llama_renderer."""
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        with (
            patch(
                "apps.cotizaciones.pdf_service.render_to_string", return_value="<html>PDF</html>"
            ) as mock_render,
            patch(
                "apps.cotizaciones.pdf_service.PdfRendererService.render_html_to_pdf",
                return_value=b"%PDF-1.4",
            ) as mock_pdf,
        ):
            from apps.cotizaciones.pdf_service import generar_pdf_cotizacion

            result = generar_pdf_cotizacion(cotizacion)
            assert result == b"%PDF-1.4"
            mock_render.assert_called_once_with(
                "cotizaciones/plantilla_cotizacion.html",
                {"cotizacion": cotizacion},
            )
            mock_pdf.assert_called_once_with("<html>PDF</html>")


class TestWhatsAppWebhook:
    """TestWhatsAppWebhook."""

    def test_webhook_sin_token_retorna_503(self):
        """test_webhook_sin_token_retorna_503."""
        from django.http import HttpRequest

        from apps.cotizaciones.views_whatsapp import IncomingWhatsAppWebhook

        req = HttpRequest()
        req.method = "POST"
        req.POST = {"From": "whatsapp:+584141234567", "Body": "Hola"}
        with (
            patch.object(IncomingWhatsAppWebhook, "_verify_signature", return_value=True),
            patch("apps.cotizaciones.views_whatsapp.settings.TWILIO_AUTH_TOKEN", None),
        ):
            view = IncomingWhatsAppWebhook()
            resp = view.post(req)
            assert resp.status_code == 503

    def test_webhook_firma_invalida_retorna_401(self):
        """test_webhook_firma_invalida_retorna_401."""
        from django.http import HttpRequest

        from apps.cotizaciones.views_whatsapp import IncomingWhatsAppWebhook

        req = HttpRequest()
        req.method = "POST"
        req.POST = {"From": "whatsapp:+584141234567", "Body": "Hola"}
        with (
            patch.object(IncomingWhatsAppWebhook, "_verify_signature", return_value=False),
            patch("apps.cotizaciones.views_whatsapp.settings.TWILIO_AUTH_TOKEN", "token_valido"),
        ):
            view = IncomingWhatsAppWebhook()
            resp = view.post(req)
            assert resp.status_code == 401

    def test_webhook_valido_encola_tarea(self):
        """test_webhook_valido_encola_tarea."""
        from django.http import HttpRequest

        from apps.cotizaciones.views_whatsapp import IncomingWhatsAppWebhook

        req = HttpRequest()
        req.method = "POST"
        req.POST = {"From": "whatsapp:+584141234567", "Body": "Quiero un vuelo a Madrid"}
        with (
            patch.object(IncomingWhatsAppWebhook, "_verify_signature", return_value=True),
            patch("apps.cotizaciones.views_whatsapp.settings.TWILIO_AUTH_TOKEN", "token_valido"),
            patch(
                "apps.cotizaciones.views_whatsapp.process_twilio_voice_quote_task.delay"
            ) as mock_task,
        ):
            view = IncomingWhatsAppWebhook()
            resp = view.post(req)
            assert resp.status_code == 200
            mock_task.assert_called_once_with(
                sender_id="whatsapp:+584141234567",
                raw_phone="+584141234567",
                body_text="Quiero un vuelo a Madrid",
                num_media=0,
                media_url="",
                media_type="",
            )

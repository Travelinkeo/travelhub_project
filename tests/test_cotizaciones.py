import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.cotizaciones.models import Cotizacion, ItemCotizacion
from apps.cotizaciones.serializers import CotizacionSerializer


@pytest.mark.django_db
class TestCotizacionModel:
    def test_crear_cotizacion_con_numero_auto(self, agencia_premium, moneda_usd):
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        assert cotizacion.numero_cotizacion.startswith("COT")
        assert cotizacion.numero_cotizacion.endswith("-0001")
        assert cotizacion.pk is not None

    def test_crear_cotizacion_con_prefijo_agencia(self, agencia_premium, moneda_usd):
        slug = agencia_premium.subdominio_slug.upper()
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        assert slug in cotizacion.numero_cotizacion

    def test_str_representation(self, agencia_premium, moneda_usd):
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        assert str(cotizacion) == cotizacion.numero_cotizacion

    def test_str_fallback_sin_numero(self):
        cotizacion = Cotizacion()
        assert hasattr(cotizacion, "numero_cotizacion")

    def test_calcular_total_con_items(self, agencia_premium, moneda_usd):
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
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        cotizacion.calcular_total()
        cotizacion.refresh_from_db()
        assert cotizacion.total_cotizado == Decimal("0.00")

    def test_convertir_a_venta_aceptada(self, agencia_premium, moneda_usd, db):
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
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            destino="Miami",
            estado=Cotizacion.EstadoCotizacion.RECHAZADA,
        )
        with pytest.raises(ValueError, match="aceptadas"):
            cotizacion.convertir_a_venta()

    def test_convertir_a_venta_borrador_raise(self, agencia_premium, moneda_usd):
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            destino="Miami",
            estado=Cotizacion.EstadoCotizacion.BORRADOR,
        )
        with pytest.raises(ValueError, match="aceptadas"):
            cotizacion.convertir_a_venta()

    def test_get_whatsapp_link_con_cliente(self, agencia_premium, moneda_usd, db):
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
    def test_crear_item(self, agencia_premium, moneda_usd):
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
        assert ItemCotizacion.TipoItem.VUELO == "VUE"
        assert ItemCotizacion.TipoItem.ALOJAMIENTO == "ALO"
        assert ItemCotizacion.TipoItem.ACTIVIDAD == "ACT"

    def test_item_default_tipo(self):
        item = ItemCotizacion(tipo_item=ItemCotizacion.TipoItem.OTRO)
        assert item.get_tipo_item_display() == "Otro"

    def test_item_str(self, agencia_premium, moneda_usd):
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
    def test_serializer_contains_expected_fields(self, agencia_premium, moneda_usd):
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
    def _setup_user_agencia(self, usuario_staff, agencia):
        from core.api import UsuarioAgencia

        UsuarioAgencia.objects.get_or_create(
            usuario=usuario_staff, agencia=agencia, defaults={"rol": "admin"}
        )

    def test_list_cotizaciones_authenticated(self, agencia_premium, moneda_usd, usuario_staff):
        self._setup_user_agencia(usuario_staff, agencia_premium)
        Cotizacion.objects.create(agencia=agencia_premium, moneda=moneda_usd, destino="Miami")
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.get("/cotizaciones/api/cotizaciones/")
        assert response.status_code == status.HTTP_200_OK

    def test_list_cotizaciones_unauthenticated(self):
        client = APIClient()
        response = client.get("/cotizaciones/api/cotizaciones/")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_create_cotizacion_authenticated(self, agencia_premium, moneda_usd, usuario_staff):
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
        self._setup_user_agencia(usuario_staff, agencia_premium)
        cotizacion = Cotizacion.objects.create(
            agencia=agencia_premium, moneda=moneda_usd, destino="Miami"
        )
        client = APIClient()
        client.force_authenticate(user=usuario_staff)
        response = client.delete(f"/cotizaciones/api/cotizaciones/{cotizacion.id_cotizacion}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

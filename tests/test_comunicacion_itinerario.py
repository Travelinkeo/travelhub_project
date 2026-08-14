from datetime import timedelta

import pytest
from django.test import RequestFactory
from django.utils import timezone

from apps.bookings.models import (
    SegmentoVuelo,
    Venta,
    VentaMensaje,
)
from apps.bookings.services.itinerary_service import ItineraryCryptoService
from apps.bookings.views.comunicacion_views import generate_ical_calendar
from apps.common.models import Ciudad, Moneda, Pais
from apps.crm.models import Cliente
from core.models import Agencia


@pytest.mark.django_db
def test_comunicacion_models_creation():
    agencia = Agencia.objects.create(nombre="Agencia Test", slug="agencia-test", rif="J-12345678-0")
    cliente = Cliente.objects.create(
        agencia=agencia, nombres="Carlos", apellidos="Perez", email="carlos@test.com"
    )
    moneda = Moneda.objects.create(codigo_iso="USD", nombre="Dólar", simbolo="$")

    venta = Venta.objects.create(
        agencia=agencia,
        cliente=cliente,
        moneda=moneda,
        localizador="TEST99",
        total_venta=1500.00,
    )

    msg = VentaMensaje.objects.create(
        venta=venta,
        direccion="OUT",
        canal="EMAIL",
        remitente="Operaciones",
        destinatario="carlos@test.com",
        cuerpo="Hola Carlos, adjunto tu itinerario.",
        enlace_ficha_digital="https://travelhub.cc/itinerary/v1/live/token123/",
    )

    assert msg.pk is not None
    assert msg.venta == venta
    assert msg.direccion == "OUT"
    assert "token123" in msg.enlace_ficha_digital


@pytest.mark.django_db
def test_itinerary_crypto_token_roundtrip():
    agencia = Agencia.objects.create(
        nombre="Agencia Crypto", slug="agencia-crypto", rif="J-99999999-0"
    )
    cliente = Cliente.objects.create(
        agencia=agencia, nombres="Ana", apellidos="Gomez", email="ana@test.com"
    )
    moneda = Moneda.objects.create(codigo_iso="USD", nombre="Dólar", simbolo="$")

    venta = Venta.objects.create(
        agencia=agencia, cliente=cliente, moneda=moneda, localizador="CRYPTO1", total_venta=500.00
    )

    url = ItineraryCryptoService.generar_enlace_itinerario(venta)
    assert "itinerary/v1/live/" in url

    # Extraer token de la URL
    token = url.split("itinerary/v1/live/")[1].rstrip("/")
    venta_id, agencia_id = ItineraryCryptoService.verificar_y_desempaquetar_token(
        token, max_age_days=30
    )

    assert venta_id == venta.pk
    assert agencia_id == agencia.pk


@pytest.mark.django_db
def test_generate_ical_calendar_endpoint():
    agencia = Agencia.objects.create(nombre="Agencia iCal", slug="agencia-ical", rif="J-88888888-0")
    cliente = Cliente.objects.create(
        agencia=agencia, nombres="Luis", apellidos="Silva", email="luis@test.com"
    )
    moneda = Moneda.objects.create(codigo_iso="USD", nombre="Dólar", simbolo="$")
    pais = Pais.objects.create(codigo_iso="VE", nombre="Venezuela")
    ciudad_ccs = Ciudad.objects.create(codigo_iata="CCS", nombre="Caracas", pais=pais)
    ciudad_mad = Ciudad.objects.create(codigo_iata="MAD", nombre="Madrid", pais=pais)

    venta = Venta.objects.create(
        agencia=agencia, cliente=cliente, moneda=moneda, localizador="ICAL01", total_venta=800.00
    )

    salida = timezone.now() + timedelta(days=5)
    llegada = salida + timedelta(hours=9)

    SegmentoVuelo.objects.create(
        venta=venta,
        aerolinea="Iberia",
        numero_vuelo="IB6673",
        origen=ciudad_ccs,
        destino=ciudad_mad,
        fecha_salida=salida,
        fecha_llegada=llegada,
        cabina="Business",
        equipaje_permitido="2PC 23KG",
    )

    url = ItineraryCryptoService.generar_enlace_itinerario(venta)
    token = url.split("itinerary/v1/live/")[1].rstrip("/")

    factory = RequestFactory()
    request = factory.get(f"/bookings/itinerary/v1/live/{token}/calendar.ics")

    response = generate_ical_calendar(request, token)

    assert response.status_code == 200
    assert response["Content-Type"] == "text/calendar; charset=utf-8"
    content = response.content.decode("utf-8")
    assert "BEGIN:VCALENDAR" in content
    assert "IB6673" in content
    assert "CCS" in content
    assert "MAD" in content

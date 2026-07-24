from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.bookings.models import BoletoImportado, Venta
from apps.common.models import Ciudad, Moneda, Pais
from apps.crm.models import Cliente
from core.models.agencia import Agencia


def create_test_agencia(**overrides: Any) -> Agencia:
    params = {
        "nombre": "Agencia Test",
        "nombre_comercial": "Agencia Test",
        "email_principal": f"test.{timezone.now().timestamp()}@travelhub.cc",
    }
    params.update(overrides)
    agencia = Agencia.objects.create(**params)
    if "subdominio_slug" not in overrides:
        config = agencia.configuracion
        config.subdominio_slug = f"test-{agencia.id}"
        config.save()
    return agencia


def create_test_user(username="testuser", is_staff=False, is_superuser=False, **overrides: Any):
    User = get_user_model()
    params = {
        "username": f"{username}_{timezone.now().timestamp()}",
        "email": f"{username}@test.com",
        "is_staff": is_staff,
        "is_superuser": is_superuser,
    }
    params.update(overrides)
    user = User.objects.create_user(**params)
    user.set_password("testpass123")
    user.save()
    return user


def create_test_cliente(**overrides: Any) -> Cliente:
    params = {
        "nombres": "Juan",
        "apellidos": "Pérez",
        "email": f"cliente.{timezone.now().timestamp()}@test.com",
    }
    params.update(overrides)
    return Cliente.objects.create(**params)


def create_test_moneda(codigo_iso="USD", **overrides: Any) -> Moneda:
    defaults = {"nombre": "Dólar", "simbolo": "$"}
    defaults.update(overrides)
    moneda, _ = Moneda.objects.get_or_create(codigo_iso=codigo_iso, defaults=defaults)
    return moneda


def create_test_pais(**overrides: Any) -> Pais:
    params = {
        "codigo_iso_2": "VE",
        "nombre": "Venezuela",
        "codigo_iso_3": "VEN",
    }
    params.update(overrides)
    pais, _ = Pais.objects.get_or_create(codigo_iso_2=params["codigo_iso_2"], defaults=params)
    return pais


def create_test_ciudad(pais: Pais | None = None, **overrides: Any) -> Ciudad:
    if pais is None:
        pais = create_test_pais()
    params = {"codigo_iata": "CCS", "nombre": "Caracas", "pais": pais}
    params.update(overrides)
    ciudad, _ = Ciudad.objects.get_or_create(codigo_iata=params["codigo_iata"], defaults=params)
    return ciudad


def create_test_venta(agencia=None, cliente=None, moneda=None, **overrides: Any) -> Venta:
    if agencia is None:
        agencia = create_test_agencia()
    if cliente is None:
        cliente = create_test_cliente()
    if moneda is None:
        moneda = create_test_moneda()
    params = {
        "agencia": agencia,
        "cliente": cliente,
        "moneda": moneda,
        "localizador": "ABC123",
        "total_venta": Decimal("500.00"),
        "estado": "PEN",
        "fecha_venta": timezone.now(),
    }
    params.update(overrides)
    return Venta.objects.create(**params)


def create_test_boleto(agencia=None, **overrides: Any) -> BoletoImportado:
    if agencia is None:
        agencia = create_test_agencia()
    params = {
        "agencia": agencia,
        "numero_boleto": "1234567890",
        "nombre_pasajero_completo": "DOE/JOHN",
        "localizador_pnr": "ABC123",
        "aerolinea_emisora": "AVIANCA",
        "total_boleto": Decimal("500.00"),
        "estado_parseo": "COM",
        "version": 1,
        "estado_emision": BoletoImportado.EstadoEmision.ORIGINAL,
    }
    params.update(overrides)
    return BoletoImportado.objects.create(**params)


def parse_drf_response(response) -> dict | list:
    from rest_framework.test import APIClient

    if isinstance(response, APIClient):
        return {}
    if hasattr(response, "data"):
        return response.data
    import json
    return json.loads(response.content) if response.content else {}

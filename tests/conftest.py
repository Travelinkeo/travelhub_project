import logging
import os
import unittest.mock
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.bookings.models import Venta
from apps.common.models import Moneda
from apps.crm.models import Cliente

# Asegurar configuración de Django incluso si pytest-django no se auto-carga
if "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
try:
    import django  # noqa: E402
    from django.conf import settings  # noqa: E402

    if not settings.configured:  # pragma: no cover
        django.setup()
except Exception:  # pragma: no cover
    # Si falla aquí, los tests fallarán luego con más contexto; evitamos romper import global.
    pass

logger = logging.getLogger(__name__)


def pytest_configure(config):
    """Override settings for tests globally."""
    import os as _os
    import socket

    from django.conf import settings

    pg_available = False
    # Intentar hosts: directo DB, luego pgbouncer, luego localhost
    # NOTA: test_db solo existe en docker-compose.test.yml, no en red producción
    hosts = ["test_db", "travelhub_db", "pgbouncer", "localhost", "127.0.0.1"]
    # Credenciales: probar primero las reales del entorno, luego defaults
    creds = set()
    db_user = _os.environ.get("DB_USER", "postgres")
    db_pass = _os.environ.get("DB_PASSWORD", "")
    if db_pass:
        creds.add((db_user, db_pass))
    creds.update([("postgres", "postgres"), ("travelhub", "travelhub")])

    for host in hosts:
        for user, password in creds:
            try:
                socket.gethostbyname(host)
                import psycopg2

                try:
                    conn = psycopg2.connect(
                        host=host,
                        port=5432,
                        user=user,
                        password=password,
                        dbname="travelhub_test",
                        connect_timeout=2,
                    )
                    conn.close()
                    pg_available = True
                    settings.DATABASES["default"]["HOST"] = host
                    settings.DATABASES["default"]["PORT"] = 5432
                    settings.DATABASES["default"]["USER"] = user
                    settings.DATABASES["default"]["PASSWORD"] = password
                    break
                except Exception:
                    continue
            except socket.gaierror:
                continue
        if pg_available:
            break

    if not pg_available:
        # Store flag; conftest session-scoped fixture will skip tests
        config._pg_unavailable = True
        return
    else:
        config._pg_unavailable = False
        # Con --nomigrations la migración 0046 (pg_trgm) no se ejecuta.
        # Forzamos pg_trgm en template1 para que toda nueva BD (incluyendo
        # test_travelhub creada por pytest-django) herede la extensión.
        _pg_created = False
        try:
            import psycopg2 as _pg_sdk

            _host = settings.DATABASES["default"]["HOST"]
            _port = settings.DATABASES["default"]["PORT"]
            _user = settings.DATABASES["default"]["USER"]
            _pass = settings.DATABASES["default"]["PASSWORD"]

            for _db in ("template1", "travelhub_test"):
                try:
                    _c = _pg_sdk.connect(
                        host=_host,
                        port=_port,
                        user=_user,
                        password=_pass,
                        dbname=_db,
                        connect_timeout=5,
                    )
                    _c.autocommit = True
                    with _c.cursor() as _cur:
                        _cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
                    _c.close()
                    _pg_created = True
                except Exception:
                    continue
        except Exception:
            pass

        if not _pg_created:
            import logging as _pg_log

            _pg_log.getLogger(__name__).warning("No se pudo crear pg_trgm en template1/test DB")

    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake-default",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake-sessions",
        },
    }

    # Monkeypatch BaseDatabaseOperations.execute_sql_flush globally to use CASCADE
    from django.db.backends.base.operations import BaseDatabaseOperations

    org_execute_sql_flush = BaseDatabaseOperations.execute_sql_flush

    def new_execute_sql_flush(self, sql_list):
        new_sql_list = []
        for sql in sql_list:
            if "TRUNCATE" in sql and "CASCADE" not in sql:
                sql_stripped = sql.strip().rstrip(";")
                sql = f"{sql_stripped} CASCADE;"
            new_sql_list.append(sql)
        return org_execute_sql_flush(self, new_sql_list)

    BaseDatabaseOperations.execute_sql_flush = new_execute_sql_flush


@pytest.fixture(autouse=True, scope="session")
def _require_pg(request):
    """Skip all tests when PostgreSQL is unavailable."""
    if getattr(request.config, "_pg_unavailable", False):
        pytest.skip(
            "PostgreSQL not available for tests. "
            "Start test containers with: docker compose -f docker-compose.test.yml up -d"
        )


@pytest.fixture(scope="session", autouse=True)
def create_stub_tables(django_db_setup, django_db_blocker):
    """Create tables for managed=False stub models so tests can use them."""
    with django_db_blocker.unblock():
        from django.db import connection, models

        from apps.finance import models_stubs as m

        stub_models = []
        for _nm in dir(m):
            _cls = getattr(m, _nm)
            if (
                isinstance(_cls, type)
                and issubclass(_cls, models.Model)
                and _cls._meta.managed is False
                and _cls._meta.db_table
            ):
                stub_models.append(_cls)

        table_names = connection.introspection.table_names()
        remaining = {mdl for mdl in stub_models if mdl._meta.db_table not in table_names}

        while remaining:
            batch = set(remaining)
            for _mdl in batch:
                try:
                    with connection.schema_editor(atomic=False) as schema_editor:
                        schema_editor.create_model(_mdl)
                    remaining.discard(_mdl)
                except Exception:
                    pass
            if remaining == batch:
                break


@pytest.fixture(autouse=True)
def use_simple_static_storage(settings):
    """For tests force a simple staticfiles storage without triggering Django 5 deprecation.

    Antes se usaba STATICFILES_STORAGE (deprecado en Django 5). Ahora ajustamos
    settings.STORAGES['staticfiles'] directamente. Mantenemos WHITENOISE_USE_FINDERS
    para compatibilidad cuando WhiteNoise está presente.
    """
    # Asegurar estructura STORAGES exista (definida en settings del proyecto)
    if hasattr(settings, "STORAGES"):
        settings.STORAGES["staticfiles"] = {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        }
    # Compat con versiones previas (no debería aplicarse aquí, pero defensivo)
    else:  # pragma: no cover
        settings.STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
    settings.WHITENOISE_USE_FINDERS = True


@pytest.fixture(autouse=True)
def mock_ai_engine(monkeypatch):
    """
    Mock global de AIEngine para evitar llamadas reales a Gemini en tests.
    Retorna un resultado de parseo exitoso por defecto.
    """
    # Mock de _ensure_configured
    monkeypatch.setattr(
        "apps.automation.services.ai_engine.AIEngine._ensure_configured",
        lambda *args, **kwargs: True,
    )

    # Mock de la llamada principal
    from apps.automation.services.ai_engine import ai_engine

    # Respuesta por defecto compatible con ResultadoParseoSchema
    default_res = {
        "boletos": [
            {
                "codigo_reserva": "MOCK12",
                "numero_boleto": "1234567890123",
                "nombre_pasajero": "DOE/JOHN",
                "solo_nombre_pasajero": "JOHN",
                "fecha_emision": "2025-01-01",
                "tarifa": 100.0,
                "impuestos": 20.0,
                "total": 120.0,
                "moneda": "USD",
                "codigo_identificacion": None,
                "agente_emisor": "MOCK_AGENT",
                "numero_iata": "12345678",
                "codigo_reserva_aerolinea": None,
                "nombre_aerolinea": "TEST AIRLINES",
                "direccion_aerolinea": None,
                "es_remision": False,
                "source_system": "SABRE",
                "confidence_score": 1.0,
                "notas_advertencia": None,
                "itinerario": [
                    {
                        "aerolinea": "TEST AIRLINES",
                        "numero_vuelo": "TS123",
                        "origen": "TEST CITY",
                        "codigo_iata_origen": "TST",
                        "fecha_salida": "2025-02-01",
                        "hora_salida": "10:00",
                        "destino": "DEST CITY",
                        "codigo_iata_destino": "DST",
                        "hora_llegada": "12:00",
                        "fecha_llegada": "2025-02-01",
                        "cabina": "Económica",
                        "clase": "Y",
                        "localizador_aerolinea": "MOCK12",
                        "equipaje": "1PC",
                    }
                ],
            }
        ]
    }

    mock_call = unittest.mock.MagicMock(return_value=default_res)
    monkeypatch.setattr(ai_engine, "call_gemini", mock_call)

    # Mock de generate_content (usado por ai_parser.py)
    import json

    # Respuesta JSON para ai_parser
    ai_parser_res = {
        "passenger": {"name": "JUAREZ/RAUL"},
        "bookingDetails": {"ticketNumber": "0457281019415"},
        "flights": [
            {
                "flightNumber": "AA123",
                "departure": {"location": "CARACAS"},
                "arrival": {"location": "BOGOTA"},
            }
        ],
    }
    monkeypatch.setattr(
        "apps.automation.services.ai_engine.generate_content",
        lambda *args, **kwargs: json.dumps(ai_parser_res),
    )

    return mock_call


@pytest.fixture
def usuario_staff(db):
    User = get_user_model()
    user, _ = User.objects.get_or_create(username="staffer")
    user.set_password("staffpass1234")
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def api_client_staff(usuario_staff):
    client = APIClient()
    client.force_login(usuario_staff)
    return client


@pytest.fixture
def usuario_api(db):
    User = get_user_model()
    user, _ = User.objects.get_or_create(username="tester")
    user.set_password("pass1234")
    user.save()
    return user


@pytest.fixture
def api_client_autenticado(usuario_api):
    client = APIClient()
    client.force_login(usuario_api)
    return client


@pytest.fixture
def venta_base(db):
    moneda, _ = Moneda.objects.get_or_create(
        codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$"}
    )
    cliente, _ = Cliente.objects.get_or_create(
        nombres="John", apellidos="Doe", email="john@example.com"
    )
    venta = Venta.objects.create(
        cliente=cliente,
        moneda=moneda,
        subtotal=Decimal("100.00"),
        impuestos=Decimal("20.00"),
        monto_pagado=Decimal("0.00"),
        descripcion_general="Venta base para tests",
    )
    return venta


# ============================================
# FIXTURES ADICIONALES PARA FASE 5
# ============================================


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock de Redis para tests de caché"""
    mock = unittest.mock.MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True

    # Suponiendo que se usa django.core.cache
    monkeypatch.setattr("django.core.cache.cache.get", mock.get)
    monkeypatch.setattr("django.core.cache.cache.set", mock.set)
    monkeypatch.setattr("django.core.cache.cache.delete", mock.delete)

    return mock


@pytest.fixture
def mock_celery_task(monkeypatch):
    """Mock de tareas Celery"""
    mock = unittest.mock.MagicMock()
    monkeypatch.setattr("core.tasks.process_ticket_async.delay", mock)
    return mock


@pytest.fixture
def sample_pais(db):
    """País de ejemplo para tests"""
    from apps.common.models import Pais

    pais, _ = Pais.objects.get_or_create(
        codigo_iso_2="VE", defaults={"nombre": "Venezuela", "codigo_iso_3": "VEN"}
    )
    return pais


@pytest.fixture
def sample_ciudad(db, sample_pais):
    """Ciudad de ejemplo para tests"""
    from apps.common.models import Ciudad

    ciudad, _ = Ciudad.objects.get_or_create(
        codigo_iata="CCS", defaults={"nombre": "Caracas", "pais": sample_pais}
    )
    return ciudad


@pytest.fixture
def agencia_premium(db):
    """Crea una agencia configurada como Contribuyente Especial (Tenant A)."""
    from core.models.agencia import Agencia

    agencia = Agencia.objects.create(
        nombre="Turismo Premium LatAn", email_principal="premium@travelhub.cc"
    )
    config = agencia.configuracion
    config.es_sujeto_pasivo_especial = True
    config.subdominio_slug = "premium"
    config.save()
    return agencia


@pytest.fixture
def agencia_estandar(db):
    """Crea una agencia estándar (Tenant B)."""
    from core.models.agencia import Agencia

    agencia = Agencia.objects.create(
        nombre="Viajes Estándar", email_principal="estandar@travelhub.cc"
    )
    config = agencia.configuracion
    config.es_sujeto_pasivo_especial = False
    config.subdominio_slug = "estandar"
    config.save()
    return agencia


@pytest.fixture
def moneda_usd(db):
    from apps.common.models import Moneda

    moneda, _ = Moneda.objects.get_or_create(
        codigo_iso="USD", defaults={"nombre": "Dólar Americano", "simbolo": "$"}
    )
    return moneda


@pytest.fixture
def moneda_ves(db):
    from apps.common.models import Moneda

    moneda, _ = Moneda.objects.get_or_create(
        codigo_iso="VES", defaults={"nombre": "Bolívares", "simbolo": "Bs"}
    )
    return moneda


# ============================================
# FIXTURES COMPARTIDAS — FASE 0+
# ============================================


@pytest.fixture
def superuser(db):
    """Crea un superusuario para tests de admin."""
    User = get_user_model()
    user = User.objects.create_superuser(
        username=f"admin_{__import__('time').time()}",
        email="admin@test.com",
        password="testpass123",
    )
    return user


@pytest.fixture
def admin_client(client, superuser):
    """Django test client autenticado como superuser."""
    client.force_login(superuser)
    return client


@pytest.fixture
def agencia(db):
    """Crea una agencia de prueba."""
    from tests.helpers import create_test_agencia

    return create_test_agencia()


@pytest.fixture
def usuario_agente(db, agencia):
    """Crea un usuario agente perteneciente a una agencia."""
    User = get_user_model()
    user = User.objects.create_user(
        username=f"agente_{__import__('time').time()}",
        email="agente@test.com",
        password="testpass123",
    )
    from core.models.agencia import UsuarioAgencia

    UsuarioAgencia.objects.create(usuario=user, agencia=agencia, rol="AGENTE")
    return user


@pytest.fixture
def mock_http_requests(monkeypatch):
    """Mock genérico de requests.post/get para evitar llamadas HTTP reales.

    Uso: mock_http_requests.post(requests.post)  # reemplaza llamadas reales
    """
    import unittest.mock

    mock = unittest.mock.MagicMock()
    monkeypatch.setattr("requests.post", mock)
    monkeypatch.setattr("requests.get", mock)
    monkeypatch.setattr("requests.put", mock)
    return mock


@pytest.fixture
def mock_provider_chain(monkeypatch):
    """
    Mock de ProviderChain/FallbackRouter para tests que necesitan
    resultados de IA pero no quieren ejecutar la cadena real.
    """
    import json
    import unittest.mock

    from apps.automation.providerchain.base import ProviderResult

    def fake_generate(**kwargs):
        return ProviderResult(
            text=json.dumps(
                {
                    "status": "ok",
                    "data": "test response",
                    "confidence": 0.95,
                }
            ),
            provider="gemini",
            model="gemini-2.0-flash",
            input_tokens=10,
            output_tokens=20,
            duration_ms=100,
            success=True,
        )

    mock_router = unittest.mock.MagicMock()
    mock_router.generate = fake_generate

    monkeypatch.setattr(
        "apps.automation.providerchain.fallback_router.fallback_router",
        mock_router,
    )
    monkeypatch.setattr(
        "apps.automation.services.ai_engine.fallback_router",
        mock_router,
    )
    return mock_router


@pytest.fixture
def mock_stripe(monkeypatch):
    """Mock de operaciones Stripe para tests de finance."""
    import unittest.mock

    mock_balance = unittest.mock.MagicMock()
    mock_balance.retrieve.return_value = {"available": [{"amount": 10000, "currency": "usd"}]}

    mock_stripe = unittest.mock.MagicMock()
    mock_stripe.Balance = mock_balance
    mock_stripe.Charge.create.return_value = {"id": "ch_mock", "status": "succeeded"}
    mock_stripe.PaymentIntent.create.return_value = {
        "id": "pi_mock",
        "status": "succeeded",
        "client_secret": "secret_mock",
    }

    monkeypatch.setattr("apps.finance.services.stripe_service.stripe", mock_stripe)
    monkeypatch.setattr("core.services.api_testers.stripe", mock_stripe)
    return mock_stripe


@pytest.fixture
def enable_db_trgm(settings):
    """Fuerza desactivación de búsqueda trigram si no disponible en test DB."""
    settings.USE_PG_TRGM = False
    return settings

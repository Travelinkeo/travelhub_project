import os
import unittest.mock
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.bookings.models import Venta
from apps.crm.models import Cliente
from apps.finance.models.currencies import Moneda

# Asegurar configuración de Django incluso si pytest-django no se auto-carga
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
try:
    import django  # noqa: E402
    from django.conf import settings  # noqa: E402
    if not settings.configured:  # pragma: no cover
        django.setup()
except Exception:  # pragma: no cover
    # Si falla aquí, los tests fallarán luego con más contexto; evitamos romper import global.
    pass

def pytest_configure(config):
    """Override settings for tests globally."""
    from django.conf import settings
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake-default",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake-sessions",
        }
    }

@pytest.fixture(autouse=True)
def use_simple_static_storage(settings):
    """For tests force a simple staticfiles storage without triggering Django 5 deprecation.

    Antes se usaba STATICFILES_STORAGE (deprecado en Django 5). Ahora ajustamos
    settings.STORAGES['staticfiles'] directamente. Mantenemos WHITENOISE_USE_FINDERS
    para compatibilidad cuando WhiteNoise está presente.
    """
    # Asegurar estructura STORAGES exista (definida en settings del proyecto)
    if hasattr(settings, 'STORAGES'):
        settings.STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
    # Compat con versiones previas (no debería aplicarse aquí, pero defensivo)
    else:  # pragma: no cover
        settings.STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
    settings.WHITENOISE_USE_FINDERS = True


@pytest.fixture(autouse=True)
def mock_ai_engine(monkeypatch):
    """
    Mock global de AIEngine para evitar llamadas reales a Gemini en tests.
    Retorna un resultado de parseo exitoso por defecto.
    """
    # Mock de _ensure_configured
    monkeypatch.setattr('apps.automation.services.ai_engine.AIEngine._ensure_configured', lambda *args, **kwargs: True)
    
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
                        "equipaje": "1PC"
                    }
                ]
            }
        ]
    }
    
    mock_call = unittest.mock.MagicMock(return_value=default_res)
    monkeypatch.setattr(ai_engine, 'call_gemini', mock_call)
    
    # Mock de generate_content (usado por ai_parser.py)
    import json
    # Respuesta JSON para ai_parser
    ai_parser_res = {
        "passenger": {"name": "JUAREZ/RAUL"},
        "bookingDetails": {"ticketNumber": "0457281019415"},
        "flights": [{"flightNumber": "AA123", "departure": {"location": "CARACAS"}, "arrival": {"location": "BOGOTA"}}]
    }
    monkeypatch.setattr('apps.automation.services.ai_engine.generate_content', lambda *args, **kwargs: json.dumps(ai_parser_res))
    
    return mock_call





@pytest.fixture
def usuario_staff(db):
    User = get_user_model()
    user, _ = User.objects.get_or_create(username='staffer')
    user.set_password('staffpass1234')
    user.is_staff = True
    user.save()
    return user

@pytest.fixture
def api_client_staff(usuario_staff):
    client = APIClient()
    client.login(username='staffer', password='staffpass1234')
    return client

@pytest.fixture
def usuario_api(db):
    User = get_user_model()
    user, _ = User.objects.get_or_create(username='tester')
    user.set_password('pass1234')
    user.save()
    return user

@pytest.fixture
def api_client_autenticado(usuario_api):
    client = APIClient()
    client.login(username='tester', password='pass1234')
    return client

@pytest.fixture
def venta_base(db):
    moneda, _ = Moneda.objects.get_or_create(codigo_iso='USD', defaults={'nombre': 'Dólar', 'simbolo': '$'})
    cliente, _ = Cliente.objects.get_or_create(nombres='John', apellidos='Doe', email='john@example.com')
    venta = Venta.objects.create(
        cliente=cliente,
        moneda=moneda,
        subtotal=Decimal('100.00'),
        impuestos=Decimal('20.00'),
        monto_pagado=Decimal('0.00'),
        descripcion_general='Venta base para tests'
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
    monkeypatch.setattr('django.core.cache.cache.get', mock.get)
    monkeypatch.setattr('django.core.cache.cache.set', mock.set)
    monkeypatch.setattr('django.core.cache.cache.delete', mock.delete)
    
    return mock

@pytest.fixture
def mock_celery_task(monkeypatch):
    """Mock de tareas Celery"""
    mock = unittest.mock.MagicMock()
    monkeypatch.setattr('core.tasks.process_ticket_async.delay', mock)
    return mock

@pytest.fixture
def sample_pais(db):
    """País de ejemplo para tests"""
    from apps.common.models import Pais
    pais, _ = Pais.objects.get_or_create(
        codigo_iso_2='VE',
        defaults={'nombre': 'Venezuela', 'codigo_iso_3': 'VEN'}
    )
    return pais

@pytest.fixture
def sample_ciudad(db, sample_pais):
    """Ciudad de ejemplo para tests"""
    from apps.common.models import Ciudad
    ciudad, _ = Ciudad.objects.get_or_create(
        codigo_iata='CCS',
        defaults={'nombre': 'Caracas', 'pais': sample_pais}
    )
    return ciudad

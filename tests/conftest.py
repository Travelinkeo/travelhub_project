import os
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from core.models.personas import Cliente
from core.models.ventas import Venta
from core.models_catalogos import Moneda

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
def mock_redis(mocker):
    """Mock de Redis para tests de caché"""
    mock = mocker.MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    return mock

@pytest.fixture
def mock_celery_task(mocker):
    """Mock de tareas Celery"""
    return mocker.patch('core.tasks.process_ticket_async.delay')

@pytest.fixture
def sample_pais(db):
    """País de ejemplo para tests"""
    from core.models_catalogos import Pais
    pais, _ = Pais.objects.get_or_create(
        codigo_iso='VE',
        defaults={'nombre': 'Venezuela'}
    )
    return pais

@pytest.fixture
def sample_ciudad(db, sample_pais):
    """Ciudad de ejemplo para tests"""
    from core.models_catalogos import Ciudad
    ciudad, _ = Ciudad.objects.get_or_create(
        codigo_iata='CCS',
        defaults={'nombre': 'Caracas', 'pais': sample_pais}
    )
    return ciudad

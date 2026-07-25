"""Tests para Tenant vault."""
from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.automation.services.ai_engine import get_gemini_api_key
from core.models import Agencia


@pytest.mark.django_db
def test_tenant_vault_encrypted_key_success():
    """
    Verifica que se cifre, guarde y descifre correctamente la clave de la agencia.
    """
    # 1. Crear la agencia
    agencia = Agencia.objects.create(nombre="Agencia Prueba Cifrada", rif="J-99999999-9")

    # 2. Guardar la clave usando la propiedad
    test_key = "AIzaSyTestKey1234567890"
    agencia.gemini_api_key = test_key

    # Recargar de BD
    agencia.refresh_from_db()

    # La clave de la propiedad descifra automáticamente
    assert agencia.gemini_api_key == test_key

    # Y está guardada en configuracion
    assert agencia.configuracion.gemini_api_key == test_key

    # Verificar que la función de resolución get_gemini_api_key devuelva la clave correcta
    resolved_key = get_gemini_api_key(agencia)
    assert resolved_key == test_key


@pytest.mark.django_db
def test_tenant_vault_fallback_to_global():
    """
    Verifica que si la agencia no tiene clave configurada, o es None,
    se use la clave global de settings o entorno.
    """
    # Agencia sin clave configurada
    agencia = Agencia.objects.create(nombre="Agencia Sin Clave", rif="J-88888888-8")

    # Mocking os.environ to make sure it falls back to settings or mocked env
    with patch.dict("os.environ", {"GEMINI_API_KEY": "env-fallback-key"}, clear=True):
        resolved_key = get_gemini_api_key(agencia)
        assert resolved_key == "env-fallback-key"

        resolved_key_none = get_gemini_api_key(None)
        assert resolved_key_none == "env-fallback-key"

    with (
        patch.dict("os.environ", {}, clear=True),
        override_settings(GEMINI_API_KEY="settings-fallback-key"),
    ):
        # Con os.environ vacío, debería caer en settings.GEMINI_API_KEY
        resolved_key = get_gemini_api_key(agencia)
        assert resolved_key == "settings-fallback-key"

        resolved_key_none = get_gemini_api_key(None)
        assert resolved_key_none == "settings-fallback-key"

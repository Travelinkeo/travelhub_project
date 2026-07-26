"""Tests extendidos para la Provider Chain — cubre cada proveedor individual."""

import unittest.mock

import pytest
from django.core.cache import cache

from apps.automation.providerchain.base import ProviderResult
from apps.automation.providerchain.health import get_health_history
from apps.automation.providerchain.registry import ProviderRegistry

pytestmark = [pytest.mark.django_db, pytest.mark.unit]


# ─── Helpers ──────────────────────────────────────────────────────


class OkProviderStub:
    """OkProviderStub."""

    provider_name = "stub_ok"
    supports_structured_output = True
    is_emergency_only = False

    def test_connection(self):
        """test_connection."""
        return True

    def generate(self, prompt, **kw):
        """generate."""
        return ProviderResult(text="ok", provider="stub_ok", success=True)


class FailProviderStub:
    """FailProviderStub."""

    provider_name = "stub_fail"
    supports_structured_output = False
    is_emergency_only = False

    def test_connection(self):
        """test_connection."""
        return False

    def generate(self, prompt, **kw):
        """generate."""
        return ProviderResult(success=False, error="fail", provider="stub_fail")


# ─── GeminiProvider ───────────────────────────────────────────────


class TestGeminiProvider:
    """TestGeminiProvider."""

    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch):
        """_setup."""
        self.mock_genai = unittest.mock.MagicMock()
        monkeypatch.setattr("google.genai", self.mock_genai)

        mock_client = unittest.mock.MagicMock()
        self.mock_genai.Client.return_value = mock_client
        self.mock_client = mock_client

        monkeypatch.setattr(
            "apps.automation.providerchain.gemini_provider.get_api_secret",
            lambda svc, default=None: "mock-key",
        )

    def test_resolve_api_key_returns_secret(self):
        """test_resolve_api_key_returns_secret."""
        from apps.automation.providerchain.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        key = provider._resolve_api_key()
        assert key == "mock-key"

    def test_resolve_api_key_returns_agency_key(self, db, monkeypatch):
        """test_resolve_api_key_returns_agency_key."""
        from apps.automation.providerchain.gemini_provider import GeminiProvider
        from core.models.agencia import Agencia

        agencia = Agencia.objects.create(nombre="Test Agency", email_principal="a@b.com")
        config = agencia.configuracion
        config.gemini_api_key = "agency-key-123"
        config.save()

        provider = GeminiProvider()
        key = provider._resolve_api_key(agency_id=agencia.id)
        assert key == "agency-key-123"

    def test_test_connection_returns_true_on_success(self):
        """test_test_connection_returns_true_on_success."""
        from apps.automation.providerchain.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        assert provider.test_connection() is True
        self.mock_client.models.get.assert_called_once()

    def test_test_connection_returns_false_on_failure(self):
        """test_test_connection_returns_false_on_failure."""
        from apps.automation.providerchain.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        self.mock_client.models.get.side_effect = Exception("API error")
        assert provider.test_connection() is False

    def test_test_connection_returns_false_without_key(self, monkeypatch):
        """test_test_connection_returns_false_without_key."""
        monkeypatch.setattr(
            "apps.automation.providerchain.gemini_provider.get_api_secret",
            lambda svc, default=None: None,
        )
        from apps.automation.providerchain.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        assert provider.test_connection() is False

    def test_generate_success(self):
        """test_generate_success."""
        from apps.automation.providerchain.gemini_provider import GeminiProvider

        mock_response = unittest.mock.MagicMock()
        mock_response.text = "Hello world"
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 20
        self.mock_client.models.generate_content.return_value = mock_response

        provider = GeminiProvider()
        result = provider.generate("test prompt")
        assert result.success is True
        assert result.text == "Hello world"
        assert result.provider == "gemini"
        assert result.input_tokens == 10

    def test_generate_failure(self):
        """test_generate_failure."""
        from apps.automation.providerchain.gemini_provider import GeminiProvider

        self.mock_client.models.generate_content.side_effect = Exception("API error")

        provider = GeminiProvider()
        result = provider.generate("test prompt")
        assert result.success is False
        assert "API error" in (result.error or "")

    def test_generate_returns_error_without_key(self, monkeypatch):
        """test_generate_returns_error_without_key."""
        monkeypatch.setattr(
            "apps.automation.providerchain.gemini_provider.get_api_secret",
            lambda svc, default=None: None,
        )
        from apps.automation.providerchain.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        result = provider.generate("test prompt")
        assert result.success is False
        assert "no configurada" in (result.error or "")


# ─── OpenAIProvider ───────────────────────────────────────────────


class TestOpenAIProvider:
    """TestOpenAIProvider."""

    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch):
        """_setup."""
        self.mock_openai = unittest.mock.MagicMock()
        monkeypatch.setattr("openai", self.mock_openai)

        monkeypatch.setattr(
            "apps.automation.providerchain.openai_provider.get_api_secret",
            lambda svc, default=None: "sk-mock-key",
        )

    def test_resolve_api_key(self):
        """test_resolve_api_key."""
        from apps.automation.providerchain.openai_provider import OpenAIProvider

        provider = OpenAIProvider()
        key = provider._resolve_api_key()
        assert key == "sk-mock-key"

    def test_test_connection_returns_true(self):
        """test_test_connection_returns_true."""
        from apps.automation.providerchain.openai_provider import OpenAIProvider

        provider = OpenAIProvider()
        self.mock_openai.OpenAI.return_value.models.list.return_value = ["gpt-4"]

        assert provider.test_connection() is True

    def test_test_connection_returns_false(self):
        """test_test_connection_returns_false."""
        from apps.automation.providerchain.openai_provider import OpenAIProvider

        provider = OpenAIProvider()
        self.mock_openai.OpenAI.side_effect = Exception("key error")
        assert provider.test_connection() is False

    def test_generate_success(self):
        """test_generate_success."""
        from apps.automation.providerchain.openai_provider import OpenAIProvider

        mock_message = unittest.mock.MagicMock()
        mock_message.content = "Hello from OpenAI"
        mock_choice = unittest.mock.MagicMock()
        mock_choice.message = mock_message
        mock_response = unittest.mock.MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20

        mock_client = unittest.mock.MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        self.mock_openai.OpenAI.return_value = mock_client

        provider = OpenAIProvider()
        result = provider.generate("test prompt")
        assert result.success is True
        assert result.text == "Hello from OpenAI"
        assert result.provider == "openai"

    def test_generate_failure(self):
        """test_generate_failure."""
        from apps.automation.providerchain.openai_provider import OpenAIProvider

        mock_client = unittest.mock.MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        self.mock_openai.OpenAI.return_value = mock_client

        provider = OpenAIProvider()
        result = provider.generate("test prompt")
        assert result.success is False


# ─── DeepSeekProvider ──────────────────────────────────────────────


class TestDeepSeekProvider:
    """TestDeepSeekProvider."""

    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch):
        """_setup."""
        self.mock_openai = unittest.mock.MagicMock()
        monkeypatch.setattr("openai", self.mock_openai)

        monkeypatch.setattr(
            "apps.automation.providerchain.deepseek_provider.get_api_secret",
            lambda svc, default=None: "sk-deepseek-key",
        )

    def test_is_emergency_only(self):
        """test_is_emergency_only."""
        from apps.automation.providerchain.deepseek_provider import DeepSeekProvider

        provider = DeepSeekProvider()
        assert provider.is_emergency_only is True
        assert provider.supports_structured_output is False

    def test_generate_success(self):
        """test_generate_success."""
        from apps.automation.providerchain.deepseek_provider import DeepSeekProvider

        mock_message = unittest.mock.MagicMock()
        mock_message.content = "DeepSeek response"
        mock_choice = unittest.mock.MagicMock()
        mock_choice.message = mock_message
        mock_response = unittest.mock.MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.completion_tokens = 10

        mock_client = unittest.mock.MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        self.mock_openai.OpenAI.return_value = mock_client

        provider = DeepSeekProvider()
        result = provider.generate("test prompt")
        assert result.success is True
        assert result.text == "DeepSeek response"
        assert result.provider == "deepseek"

    def test_generate_failure(self):
        """test_generate_failure."""
        from apps.automation.providerchain.deepseek_provider import DeepSeekProvider

        mock_client = unittest.mock.MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        self.mock_openai.OpenAI.return_value = mock_client

        provider = DeepSeekProvider()
        result = provider.generate("test prompt")
        assert result.success is False


# ─── Health History ────────────────────────────────────────────────


class TestHealthHistory:
    """TestHealthHistory."""

    def setup_method(self):
        """setup_method."""
        cache.delete("health_history")

    def test_get_health_history_empty(self):
        """test_get_health_history_empty."""
        history = get_health_history()
        assert history == []

    def test_run_checks_and_get_history(self, monkeypatch):
        """test_run_checks_and_get_history."""
        from apps.automation.providerchain.health import run_health_checks

        reg = ProviderRegistry()
        monkeypatch.setattr("apps.automation.providerchain.health.provider_registry", reg)
        monkeypatch.setattr(
            "apps.automation.providerchain.health.APISecret",
            unittest.mock.MagicMock(),
        )
        import apps.automation.providerchain.health as health_mod

        health_mod.APISecret.objects.filter.return_value.distinct.return_value = []

        class AlwaysOkProvider:
            """AlwaysOkProvider."""

            provider_name = "ok"
            supports_structured_output = True
            is_emergency_only = False

            def test_connection(self):
                """test_connection."""
                return True

            def generate(self, **kw):
                """generate."""
                return ProviderResult(text="ok", success=True)

            def get_api_key_status(self):
                """get_api_key_status."""
                return {"available": True, "last_tested": None}

        reg.register(AlwaysOkProvider())
        results = run_health_checks(force=True)

        history = get_health_history()
        assert len(history) >= 1


# ─── Registry singleton ────────────────────────────────────────────


class TestRegistrySingleton:
    """TestRegistrySingleton."""

    def test_provider_registry_is_singleton(self):
        """test_provider_registry_is_singleton."""
        from apps.automation.providerchain.registry import provider_registry as r1
        from apps.automation.providerchain.registry import provider_registry as r2

        assert r1 is r2

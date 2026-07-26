import unittest.mock

import pytest
from pydantic import BaseModel

from apps.automation.providerchain.base import ProviderResult

# ─── _clean_json_response ──────────────────────────────────────────


class TestCleanJsonResponse:
    """TestCleanJsonResponse."""

    def test_removes_markdown_fences(self):
        """test_removes_markdown_fences."""
        from apps.automation.services.ai_engine import _clean_json_response

        text = '```json\n{"key": "value"}\n```'
        assert _clean_json_response(text) == '{"key": "value"}'

    def test_removes_trailing_comment(self):
        """test_removes_trailing_comment."""
        from apps.automation.services.ai_engine import _clean_json_response

        text = '{"key": "value" // comentario\n}'
        assert _clean_json_response(text) == '{"key": "value" \n}'

    def test_removes_zero_width_chars(self):
        """test_removes_zero_width_chars."""
        from apps.automation.services.ai_engine import _clean_json_response

        text = '{\n\u200b"key": "value"\n}'
        assert _clean_json_response(text) == '{\n"key": "value"\n}'

    def test_returns_empty_object_on_empty_input(self):
        """test_returns_empty_object_on_empty_input."""
        from apps.automation.services.ai_engine import _clean_json_response

        assert _clean_json_response("") == "{}"
        assert _clean_json_response(None) == "{}"
        assert _clean_json_response("   ") == "{}"

    def test_prefers_curly_braces_over_square(self):
        """test_prefers_curly_braces_over_square."""
        from apps.automation.services.ai_engine import _clean_json_response

        text = '{"key": "value"}\n["other"]'
        assert _clean_json_response(text) == '{"key": "value"}'

    def test_handles_array_only_response(self):
        """test_handles_array_only_response."""
        from apps.automation.services.ai_engine import _clean_json_response

        text = '```\n["item1", "item2"]\n```'
        result = _clean_json_response(text)
        assert '"item1"' in result
        assert '"item2"' in result

    def test_removes_single_line_comment_on_own_line(self):
        """test_removes_single_line_comment_on_own_line."""
        from apps.automation.services.ai_engine import _clean_json_response

        text = '{\n// esto es un comentario\n"key": "value"\n}'
        assert _clean_json_response(text) == '{\n\n"key": "value"\n}'


# ─── _extract_json_aggressive ───────────────────────────────────────


class TestExtractJsonAggressive:
    """TestExtractJsonAggressive."""

    def test_extracts_json_from_noisy_text(self):
        """test_extracts_json_from_noisy_text."""
        from apps.automation.services.ai_engine import _extract_json_aggressive

        text = 'Some preamble text\n{"key": "value"}\ntrailing'
        assert _extract_json_aggressive(text) is not None

    def test_returns_none_when_no_json(self):
        """test_returns_none_when_no_json."""
        from apps.automation.services.ai_engine import _extract_json_aggressive

        assert _extract_json_aggressive("no json here") is None

    def test_removes_trailing_commas(self):
        """test_removes_trailing_commas."""
        from apps.automation.services.ai_engine import _extract_json_aggressive

        text = '{"a": 1, "b": 2,}'
        result = _extract_json_aggressive(text)
        assert result is not None
        import json as _json

        assert _json.loads(result) == {"a": 1, "b": 2}

    def test_handles_trailing_comma_in_nested(self):
        """test_handles_trailing_comma_in_nested."""
        from apps.automation.services.ai_engine import _extract_json_aggressive

        text = '{"a": {"b": 1,}}'
        result = _extract_json_aggressive(text)
        assert result is not None
        import json as _json

        assert _json.loads(result) == {"a": {"b": 1}}


# ─── _prepare_images ────────────────────────────────────────────────


class TestPrepareImages:
    """TestPrepareImages."""

    def test_returns_none_when_none_input(self):
        """test_returns_none_when_none_input."""
        from apps.automation.services.ai_engine import AIEngine

        engine = AIEngine()
        assert engine._prepare_images(None) is None
        assert engine._prepare_images([]) is None

    def test_handles_dict_with_data_key(self):
        """test_handles_dict_with_data_key."""
        from apps.automation.services.ai_engine import AIEngine

        engine = AIEngine()
        result = engine._prepare_images([{"data": b"hello"}])
        assert result == [b"hello"]

    def test_handles_raw_bytes(self):
        """test_handles_raw_bytes."""
        from apps.automation.services.ai_engine import AIEngine

        engine = AIEngine()
        result = engine._prepare_images([b"raw_bytes"])
        assert result == [b"raw_bytes"]

    def test_handles_file_like_object(self):
        """test_handles_file_like_object."""
        import io

        from apps.automation.services.ai_engine import AIEngine

        file_obj = io.BytesIO(b"file_content")
        file_obj.name = "test.png"
        engine = AIEngine()
        result = engine._prepare_images([file_obj])
        assert result == [b"file_content"]

    def test_skips_dict_without_data_key(self):
        """test_skips_dict_without_data_key."""
        from apps.automation.services.ai_engine import AIEngine

        engine = AIEngine()
        result = engine._prepare_images([{"mime_type": "image/png"}])
        assert result == []


# ─── _has_media ─────────────────────────────────────────────────────


class TestHasMedia:
    """TestHasMedia."""

    def test_false_for_none(self):
        """test_false_for_none."""
        from apps.automation.services.ai_engine import AIEngine

        assert not AIEngine()._has_media(None)
        assert not AIEngine()._has_media([])

    def test_true_for_dict_with_mime_type(self):
        """test_true_for_dict_with_mime_type."""
        from apps.automation.services.ai_engine import AIEngine

        assert AIEngine()._has_media([{"mime_type": "image/png"}])

    def test_true_for_file_like(self):
        """test_true_for_file_like."""
        import io

        from apps.automation.services.ai_engine import AIEngine

        assert AIEngine()._has_media([io.BytesIO(b"data")])

    def test_false_for_plain_dict(self):
        """test_false_for_plain_dict."""
        from apps.automation.services.ai_engine import AIEngine

        assert not AIEngine()._has_media([{"key": "value"}])


# ─── _postprocess_result ────────────────────────────────────────────


class SampleSchema(BaseModel):
    """SampleSchema."""

    name: str
    age: int


class TestPostprocessResult:
    """TestPostprocessResult."""

    def test_returns_text_when_no_schema(self):
        """test_returns_text_when_no_schema."""
        from apps.automation.services.ai_engine import AIEngine

        engine = AIEngine()
        assert engine._postprocess_result("hello", None) == "hello"

    def test_validates_against_schema(self):
        """test_validates_against_schema."""
        from apps.automation.services.ai_engine import AIEngine

        engine = AIEngine()
        text = '{"name": "Juan", "age": 30}'
        result = engine._postprocess_result(text, SampleSchema)
        assert isinstance(result, SampleSchema)
        assert result.name == "Juan"
        assert result.age == 30

    def test_returns_error_dict_on_invalid_json(self):
        """test_returns_error_dict_on_invalid_json."""
        from apps.automation.services.ai_engine import AIEngine

        engine = AIEngine()
        text = "not json at all"
        result = engine._postprocess_result(text, SampleSchema)
        assert isinstance(result, dict)
        assert "error" in result

    def test_passes_through_error_dict(self):
        """test_passes_through_error_dict."""
        from apps.automation.services.ai_engine import AIEngine

        engine = AIEngine()
        text = '{"error": "something went wrong"}'
        result = engine._postprocess_result(text, SampleSchema)
        assert result == {"error": "something went wrong"}

    def test_wraps_list_for_resultado_parseo(self):
        """test_wraps_list_for_resultado_parseo."""
        from apps.automation.services.ai_engine import AIEngine
        from core.api import ResultadoParseoSchema

        engine = AIEngine()
        text = '[{"codigo_reserva": "ABC123", "numero_boleto": "1234567890123", "nombre_pasajero": "TEST", "tarifa": 100, "impuestos": 10, "total": 110, "moneda": "USD", "itinerario": []}]'
        result = engine._postprocess_result(text, ResultadoParseoSchema)
        assert isinstance(result, ResultadoParseoSchema)
        assert len(result.boletos) == 1

    def test_wraps_dict_for_resultado_parseo(self):
        """test_wraps_dict_for_resultado_parseo."""
        from apps.automation.services.ai_engine import AIEngine
        from core.api import ResultadoParseoSchema

        engine = AIEngine()
        text = '{"codigo_reserva": "ABC123", "numero_boleto": "1234567890123", "nombre_pasajero": "TEST", "tarifa": 100, "impuestos": 10, "total": 110, "moneda": "USD", "itinerario": []}'
        result = engine._postprocess_result(text, ResultadoParseoSchema)
        assert isinstance(result, ResultadoParseoSchema)
        assert len(result.boletos) == 1
        assert result.boletos[0].codigo_reserva == "ABC123"


# ─── call_gemini (con mock de provider chain) ─────────────────────


class TestCallGemini:
    """TestCallGemini."""

    @pytest.fixture(autouse=True)
    def _setup_mocks(self, monkeypatch):
        """_setup_mocks."""
        self.mock_cache = unittest.mock.MagicMock()
        self.mock_cache.get.return_value = None
        monkeypatch.setattr("django.core.cache.cache", self.mock_cache)

        self.mock_router = unittest.mock.MagicMock()
        monkeypatch.setattr(
            "apps.automation.services.ai_engine.fallback_router",
            self.mock_router,
        )

    def test_success_no_schema(self):
        """test_success_no_schema."""
        from apps.automation.services.ai_engine import AIEngine

        self.mock_router.generate.return_value = ProviderResult(
            text="Hello world",
            provider="gemini",
            model="gemini-2.0-flash",
            success=True,
        )
        engine = AIEngine()
        result = engine.call_gemini("test prompt")
        assert result == {"text": "Hello world"}

    def test_success_with_schema(self):
        """test_success_with_schema."""
        from apps.automation.services.ai_engine import AIEngine

        self.mock_router.generate.return_value = ProviderResult(
            text='{"name": "Juan", "age": 30}',
            provider="gemini",
            model="gemini-2.0-flash",
            success=True,
        )
        engine = AIEngine()
        result = engine.call_gemini("test", response_schema=SampleSchema)
        assert isinstance(result, SampleSchema)
        assert result.name == "Juan"

    def test_failure_returns_error_dict(self):
        """test_failure_returns_error_dict."""
        from apps.automation.services.ai_engine import AIEngine

        self.mock_router.generate.return_value = ProviderResult(
            success=False,
            error="API error",
            provider="gemini",
        )
        engine = AIEngine()
        result = engine.call_gemini("test")
        assert "error" in result
        assert "API error" in result["error"]

    def test_circuit_breaker_triggers_after_5_fails(self):
        """test_circuit_breaker_triggers_after_5_fails."""
        from apps.automation.services.ai_engine import AIEngine

        self.mock_cache.get.return_value = None
        self.mock_router.generate.return_value = ProviderResult(
            success=False, error="fail", provider="gemini"
        )
        engine = AIEngine()
        for _ in range(5):
            engine.call_gemini("test")

        assert self.mock_cache.set.call_count >= 1

    @pytest.mark.skip(reason="Requiere mock de AIUsageLog")
    def test_logs_usage_on_success(self):
        """test_logs_usage_on_success."""
        pass


# ─── generate_content (standalone wrapper) ────────────────────────


class TestGenerateContent:
    """TestGenerateContent."""

    @pytest.fixture(autouse=True)
    def _mock_ai_engine(self, monkeypatch):
        """_mock_ai_engine."""
        self.mock_result = {"text": "hola mundo"}
        monkeypatch.setattr(
            "apps.automation.services.ai_engine.ai_engine",
            unittest.mock.MagicMock(),
        )
        monkeypatch.setattr(
            "apps.automation.services.ai_engine.ai_engine.call_gemini",
            unittest.mock.MagicMock(return_value=self.mock_result),
        )

    def test_returns_text_from_dict(self):
        """test_returns_text_from_dict."""
        from apps.automation.services.ai_engine import generate_content

        result = generate_content("test prompt")
        assert result == "hola mundo"

    def test_returns_string_on_exception(self):
        """test_returns_string_on_exception."""
        import apps.automation.services.ai_engine as engine_mod
        from apps.automation.services.ai_engine import generate_content

        engine_mod.ai_engine.call_gemini.side_effect = Exception("boom")
        result = generate_content("test")
        assert result == ""


# ─── analizar_documento_con_gemini_estructurado ───────────────────


class TestAnalizarDocumento:
    """TestAnalizarDocumento."""

    @pytest.fixture(autouse=True)
    def _mock_router(self, monkeypatch):
        """_mock_router."""
        self.mock_router = unittest.mock.MagicMock()
        monkeypatch.setattr(
            "apps.automation.services.ai_engine.fallback_router",
            self.mock_router,
        )

    def test_success_returns_parsed_json(self):
        """test_success_returns_parsed_json."""
        from apps.automation.services.ai_engine import (
            analizar_documento_con_gemini_estructurado,
        )

        self.mock_router.generate.return_value = ProviderResult(
            text='{"status": "ok"}',
            provider="gemini",
            success=True,
        )
        result = analizar_documento_con_gemini_estructurado(
            b"file_content", "application/pdf", "test prompt", None
        )
        assert result == {"status": "ok"}

    def test_raises_value_error_on_bad_json(self):
        """test_raises_value_error_on_bad_json."""
        from apps.automation.services.ai_engine import (
            analizar_documento_con_gemini_estructurado,
        )

        self.mock_router.generate.return_value = ProviderResult(
            text="not json", provider="gemini", success=True
        )
        with pytest.raises(ValueError, match="no devolvió un JSON"):
            analizar_documento_con_gemini_estructurado(b"file", "application/pdf", "prompt", None)

    def test_raises_value_error_on_failure(self):
        """test_raises_value_error_on_failure."""
        from apps.automation.services.ai_engine import (
            analizar_documento_con_gemini_estructurado,
        )

        self.mock_router.generate.return_value = ProviderResult(
            success=False, error="API error", provider="gemini"
        )
        with pytest.raises(ValueError, match="Todos los proveedores fallaron"):
            analizar_documento_con_gemini_estructurado(b"file", "application/pdf", "prompt", None)


# ─── get_gemini_api_key ────────────────────────────────────────────


class TestGetGeminiApiKey:
    """TestGetGeminiApiKey."""

    def test_returns_api_secret_when_no_agency(self, monkeypatch):
        """test_returns_api_secret_when_no_agency."""
        monkeypatch.setattr(
            "apps.automation.services.ai_engine.get_api_secret",
            lambda svc, default=None: "mock-key-from-secret",
        )
        monkeypatch.setattr(
            "apps.automation.services.ai_engine.settings",
            unittest.mock.MagicMock(GEMINI_API_KEY=None),
        )
        from apps.automation.services.ai_engine import get_gemini_api_key

        key = get_gemini_api_key(agency=None)
        assert key == "mock-key-from-secret"

    def test_returns_none_when_no_key_available(self, monkeypatch):
        """test_returns_none_when_no_key_available."""
        monkeypatch.setattr(
            "apps.automation.services.ai_engine.get_api_secret",
            lambda svc, default=None: None,
        )
        monkeypatch.setattr(
            "apps.automation.services.ai_engine.settings",
            unittest.mock.MagicMock(GEMINI_API_KEY=None),
        )
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        from apps.automation.services.ai_engine import get_gemini_api_key

        key = get_gemini_api_key(agency=None)
        assert key is None


# ─── list_available_models ─────────────────────────────────────────


class TestListAvailableModels:
    """TestListAvailableModels."""

    def test_returns_error_when_no_key(self, monkeypatch):
        """test_returns_error_when_no_key."""
        monkeypatch.setattr(
            "apps.automation.services.ai_engine.get_gemini_api_key",
            lambda agency=None: None,
        )
        from apps.automation.services.ai_engine import list_available_models

        result = list_available_models()
        assert "error" in result.lower() or "configura" in str(result).lower()


# ─── _log_usage ─────────────────────────────────────────────────────


class TestLogUsage:
    """TestLogUsage."""

    @pytest.fixture(autouse=True)
    def _mock_ai_usage_log(self, monkeypatch):
        """_mock_ai_usage_log."""
        mock_model = unittest.mock.MagicMock()
        mock_model.objects.create.return_value = unittest.mock.MagicMock()
        monkeypatch.setattr(
            "apps.automation.services.ai_engine.AIUsageLog",
            mock_model,
        )
        return mock_model

    def test_creates_log_record(self, db, _mock_ai_usage_log):
        """test_creates_log_record."""
        from apps.automation.services.ai_engine import AIEngine

        engine = AIEngine()
        engine._log_usage(None, "gemini-2.0-flash", "test", 10, 20, "SUCCESS")


# ─── parse_structured_data ─────────────────────────────────────────


class TestParseStructuredData:
    """TestParseStructuredData."""

    def test_delegates_to_call_gemini(self, monkeypatch):
        """test_delegates_to_call_gemini."""
        from apps.automation.services.ai_engine import AIEngine

        mock_call = unittest.mock.MagicMock(return_value={"text": "ok"})
        monkeypatch.setattr(AIEngine, "call_gemini", mock_call)
        engine = AIEngine()
        engine.parse_structured_data("prompt", SampleSchema)
        mock_call.assert_called_once()
        args, kwargs = mock_call.call_args
        assert "prompt" in args or kwargs.get("prompt") == "prompt"


# ─── analyze_gds_terminal ──────────────────────────────────────────


class TestAnalyzeGdsTerminal:
    """TestAnalyzeGdsTerminal."""

    def test_delegates_to_call_gemini(self, monkeypatch):
        """test_delegates_to_call_gemini."""
        from apps.automation.services.ai_engine import AIEngine

        mock_call = unittest.mock.MagicMock(return_value={"text": "ok"})
        monkeypatch.setattr(AIEngine, "call_gemini", mock_call)
        engine = AIEngine()
        engine.analyze_gds_terminal("raw text", "SABRE")
        mock_call.assert_called_once()
        args, kwargs = mock_call.call_args
        assert "feature" in kwargs
        assert kwargs["feature"] == "gds_parsing"

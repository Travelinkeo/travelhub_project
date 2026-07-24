import logging
import time

from core.api import get_api_secret
from core.models import AgenciaConfiguracion

from .base import AbstractBaseProvider, ProviderResult
from .tracing import record_call

logger = logging.getLogger(__name__)

MODEL_PRO = "gemini-2.5-flash"
MODEL_FLASH = "gemini-2.5-flash-8b"


class GeminiProvider(AbstractBaseProvider):
    provider_name = "gemini"
    supports_structured_output = True

    def _resolve_api_key(self, agency_id: int | None = None) -> str | None:
        if agency_id:
            try:
                config = AgenciaConfiguracion.objects.filter(agencia_id=agency_id).first()
                if config and config.gemini_api_key:
                    return config.gemini_api_key
            except Exception:
                logger.exception("Error al obtener API key de agencia %s", agency_id)
        return get_api_secret("GEMINI_API_KEY") or get_api_secret("GOOGLE_API_KEY")

    def test_connection(self) -> bool:
        key = self._resolve_api_key()
        if not key:
            return False
        try:
            import google.genai as genai

            client = genai.Client(api_key=key)
            client.models.get(MODEL_FLASH)
            return True
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        *,
        images: list | None = None,
        schema: type | None = None,
        agency_id: int | None = None,
        feature: str = "unknown",
    ) -> ProviderResult:
        import google.genai as genai
        from google.genai import types as genai_types

        start = time.monotonic()
        key = self._resolve_api_key(agency_id)
        if not key:
            return ProviderResult(
                success=False, error="GEMINI_API_KEY no configurada", provider="gemini"
            )

        try:
            client = genai.Client(api_key=key)
            model = MODEL_PRO if not images else MODEL_FLASH
            contents = [prompt]

            if images:
                from google.genai.types import Blob, Part

                for img in images:
                    contents.append(Part(inline_data=Blob(mime_type="image/jpeg", data=img)))

            kwargs = {"contents": [prompt]}
            if schema:
                kwargs["config"] = genai_types.GenerateContentConfig(
                    response_mime_type="application/json", response_schema=schema
                )

            response = client.models.generate_content(model=model, **kwargs)
            text = response.text or ""
            duration = int((time.monotonic() - start) * 1000)
            tokens_in = (
                getattr(response, "usage_metadata", None)
                and (getattr(response.usage_metadata, "prompt_token_count", 0) or 0)
                or 0
            )
            tokens_out = (
                getattr(response, "usage_metadata", None)
                and (getattr(response.usage_metadata, "candidates_token_count", 0) or 0)
                or 0
            )

            record_call("gemini", model, duration, tokens_in, tokens_out, feature=feature)

            return ProviderResult(
                text=text,
                provider="gemini",
                model=model,
                input_tokens=tokens_in,
                output_tokens=tokens_out,
                duration_ms=duration,
                schema_used=schema is not None,
            )
        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            err_str = str(e)
            record_call(
                "gemini",
                model if "model" in dir() else "unknown",
                duration,
                0,
                0,
                success=False,
                feature=feature,
                error_str=err_str,
            )
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                logger.warning("Gemini: cuota agotada (%s)", err_str[:80])
            elif "404" in err_str or "not found" in err_str.lower():
                logger.warning(
                    "Gemini: modelo no encontrado, reintentando sin schema (%s)", err_str[:80]
                )
            else:
                logger.error("Gemini: error inesperado: %s", err_str[:200])

            return ProviderResult(success=False, error=err_str[:500], provider="gemini")

import logging
import time

from core.api import get_api_secret

from .base import AbstractBaseProvider, ProviderResult
from .tracing import record_call

logger = logging.getLogger(__name__)

MODEL_DEFAULT = "gpt-4o-mini"
MODEL_STRUCTURED = "gpt-4o-mini"


class OpenAIProvider(AbstractBaseProvider):
    provider_name = "openai"
    supports_structured_output = True

    def _get_client(self):
        import openai

        key = get_api_secret("OPENAI_API_KEY")
        if not key:
            return None
        return openai.OpenAI(api_key=key)

    def test_connection(self) -> bool:
        client = self._get_client()
        if not client:
            return False
        try:
            client.models.retrieve(MODEL_DEFAULT)
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
        start = time.monotonic()
        client = self._get_client()
        if not client:
            return ProviderResult(
                success=False, error="OPENAI_API_KEY no configurada", provider="openai"
            )

        try:
            model = MODEL_STRUCTURED if schema else MODEL_DEFAULT
            kwargs = {"model": model, "messages": [{"role": "user", "content": prompt}]}

            if images:
                content = [{"type": "text", "text": prompt}]
                for img in images:
                    import base64

                    b64 = base64.b64encode(img).decode("utf-8") if isinstance(img, bytes) else img
                    content.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        }
                    )
                kwargs["messages"] = [{"role": "user", "content": content}]

            if schema:
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
                }

            response = client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            text = choice.message.content or ""
            duration = int((time.monotonic() - start) * 1000)
            usage = response.usage
            tokens_in = usage.prompt_tokens if usage else 0
            tokens_out = usage.completion_tokens if usage else 0

            record_call("openai", model, duration, tokens_in, tokens_out, feature=feature)

            return ProviderResult(
                text=text,
                provider="openai",
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
                "openai",
                "openai",
                duration,
                0,
                0,
                success=False,
                feature=feature,
                error_str=err_str,
            )
            logger.error("OpenAI: error: %s", err_str[:200])
            return ProviderResult(success=False, error=err_str[:500], provider="openai")

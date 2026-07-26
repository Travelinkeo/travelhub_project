import logging
import time

from core.api import get_api_secret

from .base import AbstractBaseProvider, ProviderResult
from .tracing import record_call

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
MODEL_DEFAULT = "deepseek-chat"


class DeepSeekProvider(AbstractBaseProvider):
    """DeepSeekProvider."""

    provider_name = "deepseek"
    supports_structured_output = False
    is_emergency_only = True

    def _get_client(self):
        """_get_client."""
        import openai

        key = get_api_secret("DEEPSEEK_API_KEY")
        if not key:
            return None
        return openai.OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL)

    def test_connection(self) -> bool:
        """test_connection."""
        client = self._get_client()
        if not client:
            return False
        try:
            client.models.list()
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
        """generate."""
        start = time.monotonic()
        client = self._get_client()
        if not client:
            return ProviderResult(
                success=False, error="DEEPSEEK_API_KEY no configurada", provider="deepseek"
            )

        try:
            response = client.chat.completions.create(
                model=MODEL_DEFAULT,
                messages=[{"role": "user", "content": prompt}],
            )
            choice = response.choices[0]
            text = choice.message.content or ""
            duration = int((time.monotonic() - start) * 1000)
            usage = response.usage
            tokens_in = usage.prompt_tokens if usage else 0
            tokens_out = usage.completion_tokens if usage else 0

            record_call("deepseek", MODEL_DEFAULT, duration, tokens_in, tokens_out, feature=feature)

            return ProviderResult(
                text=text,
                provider="deepseek",
                model=MODEL_DEFAULT,
                input_tokens=tokens_in,
                output_tokens=tokens_out,
                duration_ms=duration,
            )
        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            err_str = str(e)
            record_call(
                "deepseek",
                MODEL_DEFAULT,
                duration,
                0,
                0,
                success=False,
                feature=feature,
                error_str=err_str,
            )
            logger.error("DeepSeek: error: %s", err_str[:200])
            return ProviderResult(success=False, error=err_str[:500], provider="deepseek")

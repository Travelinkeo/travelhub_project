import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AutomationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.automation"
    label = "automation"
    verbose_name = "Automatización y AI Parsing"

    def ready(self):
        _register_providers()


def _register_providers():
    """Registra los proveedores de IA en el ProviderRegistry."""
    from apps.automation.providerchain.deepseek_provider import DeepSeekProvider
    from apps.automation.providerchain.fallback_router import provider_registry
    from apps.automation.providerchain.gemini_provider import GeminiProvider
    from apps.automation.providerchain.openai_provider import OpenAIProvider

    provider_registry.register(GeminiProvider())
    provider_registry.register(OpenAIProvider())
    provider_registry.register(DeepSeekProvider())

    logger.info(
        "ProviderChain: %d proveedores registrados",
        len(provider_registry.all()),
    )

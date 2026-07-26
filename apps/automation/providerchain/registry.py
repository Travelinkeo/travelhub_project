import logging

from django.core.cache import cache

from apps.automation.providerchain.base import AbstractBaseProvider

logger = logging.getLogger(__name__)

# Circuit breaker TTL (60 minutos)
CIRCUIT_TTL = 60 * 60


class ProviderRegistry:
    """ProviderRegistry."""

    def __init__(self):
        """__init__."""
        self._providers: dict[str, AbstractBaseProvider] = {}

    def register(self, provider: AbstractBaseProvider) -> None:
        """register."""
        self._providers[provider.provider_name] = provider
        logger.info("Provider registrado: %s", provider.provider_name)

    def get(self, name: str) -> AbstractBaseProvider | None:
        """get."""
        return self._providers.get(name)

    def all(self) -> list[AbstractBaseProvider]:
        """all."""
        return list(self._providers.values())

    def available(self) -> list[AbstractBaseProvider]:
        """available."""
        return [p for p in self._providers.values() if not self._circuit_open(p.provider_name)]

    def fallback_chain(self, needs_structured: bool = True) -> list[AbstractBaseProvider]:
        """Retorna proveedores ordenados por prioridad, filtrando por capacidades."""
        chain = []
        for name in ["gemini", "openai", "deepseek"]:
            p = self._providers.get(name)
            if not p:
                continue
            if self._circuit_open(name):
                logger.debug("Circuit breaker abierto para %s — omitiendo", name)
                continue
            if needs_structured and not p.supports_structured_output:
                continue
            if needs_structured and p.is_emergency_only:
                continue
            chain.append(p)
        return chain

    def _circuit_open(self, provider_name: str) -> bool:
        """_circuit_open."""
        return cache.get(f"provider_circuit:{provider_name}") is not None

    def open_circuit(self, provider_name: str) -> None:
        """open_circuit."""
        cache.set(f"provider_circuit:{provider_name}", "open", CIRCUIT_TTL)
        logger.warning("Circuit breaker ABIERTO para %s (%ds)", provider_name, CIRCUIT_TTL)

    def close_circuit(self, provider_name: str) -> None:
        """close_circuit."""
        cache.delete(f"provider_circuit:{provider_name}")
        logger.info("Circuit breaker CERRADO para %s", provider_name)

    def get_health_cache_key(self) -> str:
        """get_health_cache_key."""
        return "provider_health_last_run"


provider_registry = ProviderRegistry()

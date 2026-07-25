"""Proveedor de IA/configuración para automation: base.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderResult:
    """Clase ProviderResult. Uso: según contexto de la aplicación.
    """
    text: str = ""
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0
    success: bool = True
    error: str | None = None
    schema_used: bool = False


class AbstractBaseProvider:
    """Clase AbstractBaseProvider. Uso: según contexto de la aplicación.
    """
    provider_name: str = ""
    supports_structured_output: bool = False
    is_emergency_only: bool = False

    @abstractmethod
    def test_connection(self) -> bool: ...

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        images: list[Any] | None = None,
        schema: type | None = None,
        agency_id: int | None = None,
        feature: str = "unknown",
    ) -> ProviderResult: ...

    def get_api_key_status(self) -> dict:
        # test_connection: Test connection. Args: según implementación. Returns: según implementación.
        return {"available": False, "last_tested": None}

    def cleanup(self) -> None:
        # cleanup: Cleanup. Args: según implementación. Returns: según implementación.
        if hasattr(self, "_client") and self._client:
            self._client.close()

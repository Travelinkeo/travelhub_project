from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderResult:
    text: str = ""
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0
    success: bool = True
    error: str | None = None
    schema_used: bool = False


class AbstractBaseProvider(ABC):
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
        return {"available": False, "last_tested": None}

    def cleanup(self) -> None:
        if hasattr(self, "_client") and self._client:
            self._client.close()

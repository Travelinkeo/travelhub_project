"""Proveedor de IA/configuración para automation: fallback router.
"""

import logging
from typing import Any

from .base import ProviderResult
from .registry import provider_registry

logger = logging.getLogger(__name__)


class FallbackRouter:
    """
    Enruta una solicitud a través de la cadena de proveedores,
    intentando cada uno en orden hasta obtener una respuesta exitosa.
    """

    def generate(
        self,
        prompt: str,
        *,
        images: list[Any] | None = None,
        schema: type | None = None,
        agency_id: int | None = None,
        feature: str = "unknown",
    ) -> ProviderResult:
        # generate: Genera . Args: parámetros de generación. Returns: resultado generado.
        chain = provider_registry.fallback_chain(needs_structured=schema is not None)

        if not chain:
            logger.error("No hay proveedores disponibles en la cadena de fallback")
            return ProviderResult(success=False, error="No hay proveedores disponibles")

        last_error: str | None = None

        for provider in chain:
            result = provider.generate(
                prompt=prompt,
                images=images,
                schema=schema,
                agency_id=agency_id,
                feature=feature,
            )
            if result.success:
                if result.provider != chain[0].provider_name:
                    logger.info(
                        "Fallback activado: %s -> %s (feature=%s)",
                        chain[0].provider_name,
                        result.provider,
                        feature,
                    )
                return result

            last_error = result.error
            logger.warning(
                "Proveedor %s falló para feature=%s: %s",
                provider.provider_name,
                feature,
                result.error[:100] if result.error else "sin error",
            )

            # Abrir circuit breaker si no es el último proveedor
            if provider != chain[-1]:
                provider_registry.open_circuit(provider.provider_name)

        return ProviderResult(
            success=False, error=f"Todos los proveedores fallaron. Último: {last_error}"
        )

    def test_all(self) -> list[dict]:
        """Prueba la conexión de todos los proveedores registrados."""
        results = []
        for provider in provider_registry.all():
            ok = provider.test_connection()
            results.append(
                {
                    "name": provider.provider_name,
                    "available": ok,
                    "supports_structured": provider.supports_structured_output,
                    "is_emergency": provider.is_emergency_only,
                }
            )
            if ok:
                provider_registry.close_circuit(provider.provider_name)
            else:
                logger.warning("Health check falló para %s", provider.provider_name)
        return results


fallback_router = FallbackRouter()

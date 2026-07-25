"""Servicio de circuit breaker para la aplicación common.
"""

import logging
import time
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState:
    """Clase CircuitState. Uso: según contexto de la aplicación.
    """
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open and service is unavailable."""

    pass


class CircuitBreaker:
    """
    Implementación de Circuit Breaker para resiliencia de APIs externas.

    Estados:
    - CLOSED: El sistema funciona normalmente.
    - OPEN: El sistema bloquea las llamadas para evitar sobrecarga/errores constantes.
    - HALF_OPEN: El sistema permite una llamada de prueba para ver si el servicio se recuperó.

    Uso:
        @whatsapp_circuit_breaker
        def send_message(...):
            # send_message: Envía  message. Args: datos del mensaje. Returns: resultado del envío.
            ...

        # O manualmente:
        result = whatsapp_circuit_breaker.call(send_message, ...)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        fallback: Callable[..., Any] | None = None,
    ) -> None:
        # __init__: Inicializa una nueva instancia de CircuitBreaker. Args: parámetros de inicialización.
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.fallback = fallback  # Función fallback cuando el circuito está abierto

        self.state: CircuitState = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time: float = 0
        self.success_count = 0
        self.failure_count = 0

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        # call: Call. Args: según implementación. Returns: según implementación.
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"🔄 Circuit Breaker [{self.name}] moving to HALF_OPEN state.")
            else:
                logger.warning(f"🚫 Circuit Breaker [{self.name}] is OPEN. Blocking call.")
                if self.fallback:
                    return self.fallback(*args, **kwargs)
                return {"error": f"Circuit breaker {self.name} is open. Service unavailable."}

        try:
            result = func(*args, **kwargs)

            # Detectar errores en resultados (para servicios que retornan dicts con 'error')
            if isinstance(result, dict) and "error" in result:
                self._record_failure()
                return result

            # Detectar errores por código de estado HTTP
            if hasattr(result, "status_code") and result.status_code >= 500:
                self._record_failure()
                return result

            self._record_success()
            return result

        except CircuitBreakerError:
            raise
        except Exception as e:
            self._record_failure()
            raise e

    def _record_success(self) -> None:
        # _record_success:  record success. Args: según implementación. Returns: según implementación.
        self.success_count += 1
        if self.state != CircuitState.CLOSED:
            logger.info(f"✅ Circuit Breaker [{self.name}] restored. Moving to CLOSED state.")
        self.state = CircuitState.CLOSED
        self.failures = 0

    def _record_failure(self) -> None:
        # _record_failure:  record failure. Args: según implementación. Returns: según implementación.
        self.failure_count += 1
        self.failures += 1
        self.last_failure_time = time.time()

        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                f"💥 Circuit Breaker [{self.name}] OPENED after {self.failures} failures (total: {self.failure_count})."
            )

    def get_stats(self) -> dict[str, Any]:
        """Return circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self.failures,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
        }

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time = 0
        logger.info(f"🔧 Circuit Breaker [{self.name}] manually reset.")

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        # __call__:   call  . Args: según implementación. Returns: según implementación.
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # wrapper: Wrapper. Args: según implementación. Returns: según implementación.
            return self.call(func, *args, **kwargs)

        return wrapper


# =============================================================================
# INSTANCIAS COMPARTIDAS POR SERVICIO
# =============================================================================

# AI / Gemini: Umbral bajo (3 fallos) porque es caro y propenso a rate limits
ai_circuit_breaker = CircuitBreaker(
    name="Gemini-AI",
    failure_threshold=3,
    recovery_timeout=120,
    fallback=lambda *args, **kwargs: {
        "error": "AI service temporarily unavailable. Please try again later."
    },
)

# WhatsApp / Evolution API: Umbral medio (5 fallos) porque es crítico para notificaciones
whatsapp_circuit_breaker = CircuitBreaker(
    name="Evolution-WhatsApp",
    failure_threshold=5,
    recovery_timeout=180,
    fallback=lambda *args, **kwargs: {
        "error": "WhatsApp service temporarily unavailable. Message queued for retry."
    },
)

# Email / Resend: Umbral alto (8 fallos) porque es menos crítico
email_circuit_breaker = CircuitBreaker(
    name="Resend-Email",
    failure_threshold=8,
    recovery_timeout=300,
    fallback=lambda *args, **kwargs: {"error": "Email service temporarily unavailable."},
)

# Telegram: Umbral alto (8 fallos) porque es solo para notificaciones internas
telegram_circuit_breaker = CircuitBreaker(
    name="Telegram",
    failure_threshold=8,
    recovery_timeout=300,
    fallback=lambda *args, **kwargs: {"error": "Telegram service temporarily unavailable."},
)

# Stripe: Umbral bajo (3 fallos) porque es crítico para pagos
stripe_circuit_breaker = CircuitBreaker(
    name="Stripe",
    failure_threshold=3,
    recovery_timeout=60,
    fallback=lambda *args, **kwargs: {
        "error": "Payment service temporarily unavailable. Please try again later."
    },
)

# Todos los circuit breakers en un diccionario para monitoreo
ALL_CIRCUIT_BREAKERS = {
    "ai": ai_circuit_breaker,
    "whatsapp": whatsapp_circuit_breaker,
    "email": email_circuit_breaker,
    "telegram": telegram_circuit_breaker,
    "stripe": stripe_circuit_breaker,
}

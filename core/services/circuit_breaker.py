import time
import logging
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    """
    Implementación básica de Circuit Breaker para resiliencia de APIs.
    
    Estados:
    - CLOSED: El sistema funciona normalmente.
    - OPEN: El sistema bloquea las llamadas para evitar sobrecarga/errores constantes.
    - HALF_OPEN: El sistema permite una llamada de prueba para ver si el servicio se recuperó.
    """
    
    def __init__(self, name, failure_threshold=5, recovery_timeout=60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time = 0
        
    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"🔄 Circuit Breaker [{self.name}] moving to HALF_OPEN state.")
            else:
                logger.warning(f"🚫 Circuit Breaker [{self.name}] is OPEN. Blocking call.")
                return {"error": f"Circuit breaker {self.name} is open. Service unavailable."}
        
        try:
            result = func(*args, **kwargs)
            
            # Si el resultado es un error (específico para nuestro AIEngine)
            if isinstance(result, dict) and "error" in result:
                self._record_failure()
                return result
                
            self._record_success()
            return result
            
        except Exception as e:
            self._record_failure()
            raise e

    def _record_success(self):
        if self.state != CircuitState.CLOSED:
            logger.info(f"✅ Circuit Breaker [{self.name}] restored. Moving to CLOSED state.")
        self.state = CircuitState.CLOSED
        self.failures = 0

    def _record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"💥 Circuit Breaker [{self.name}] OPENED after {self.failures} failures.")
            
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper

# Instancias compartidas
ai_circuit_breaker = CircuitBreaker("Gemini-AI", failure_threshold=3, recovery_timeout=120)

import logging
import threading
import traceback
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_thread_locals = threading.local()


def are_signals_blocked():
    """
    Checks if custom signals are currently blocked for the current thread.
    """
    return getattr(_thread_locals, "signals_blocked", False)


@contextmanager
def disable_signals():
    """
    Context manager to temporarily disable all custom business logic Django signals.
    Uso exclusivo para: migraciones, operaciones bulk, y setup de tests.

    ADVERTENCIA: Deshabilitar señales omite auditoría, asientos contables
    automáticos, y validaciones de negocio. Usar solo cuando sea estrictamente
    necesario y asegurarse de que las operaciones se auditan por otros medios.
    """
    previous = getattr(_thread_locals, "signals_blocked", False)
    _thread_locals.signals_blocked = True
    caller = "".join(traceback.format_stack()[:-1])
    logger.warning("Señales de negocio DESHABILITADAS. Caller stack:\n%s", caller)
    try:
        yield
    finally:
        _thread_locals.signals_blocked = previous
        logger.info("Señales de negocio RESTAURADAS.")

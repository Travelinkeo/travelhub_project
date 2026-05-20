import threading
from contextlib import contextmanager

_thread_locals = threading.local()

def are_signals_blocked():
    """
    Checks if custom signals are currently blocked for the current thread.
    """
    return getattr(_thread_locals, 'signals_blocked', False)

@contextmanager
def disable_signals():
    """
    Context manager to temporarily disable all custom business logic Django signals.
    Usage:
        with disable_signals():
            # Perform bulk operations, migrations, or testing setup here
            my_model.save()
    """
    previous = getattr(_thread_locals, 'signals_blocked', False)
    _thread_locals.signals_blocked = True
    try:
        yield
    finally:
        _thread_locals.signals_blocked = previous

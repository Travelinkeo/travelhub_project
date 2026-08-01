import logging
import time
from contextlib import contextmanager

from django.db import connection

logger = logging.getLogger(__name__)


@contextmanager
def rls_session_context(tenant_id: str, bypass_rls: bool = False, is_admin_path: bool = False):
    """
    Context manager para configurar RLS (Row Level Security) en PostgreSQL.

    Establece las variables de sesión `app.current_agencia_id` y `app.bypass_rls`
    para que las policies de RLS filtren automáticamente por agencia.

    Args:
        tenant_id: ID de la agencia (tenant) o "0" para sin tenant
        bypass_rls: Si True, deshabilita RLS (solo para superusers en /admin/)
        is_admin_path: Si la request es a /admin/ (para auto-bypass)
    """
    if connection.connection is None:
        yield
        return

    start = time.monotonic()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL app.current_agencia_id = %s", [tenant_id])
            cursor.execute("SET LOCAL app.bypass_rls = %s", ["true" if bypass_rls else "false"])
        yield
    except Exception as e:
        logger.error(f"Error setting RLS context: {e}")
        # No re-raise - RLS failure shouldn't break the request
        yield
    finally:
        elapsed = time.monotonic() - start
        if elapsed > 0.1:  # Log slow RLS setup (>100ms)
            logger.warning(f"RLS context setup took {elapsed:.3f}s")

        # Resetear contexto RLS al finalizar
        try:
            if connection.connection is not None:
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL app.current_agencia_id = '0'")
                    cursor.execute("SET LOCAL app.bypass_rls = 'false'")
        except Exception as e:
            logger.debug(f"Error resetting database RLS context: {e}")


def get_rls_bypass_flag(user, request_path: str, is_impersonating: bool) -> bool:
    """
    Determina si se debe hacer bypass de RLS.

    Solo superusers en /admin/ sin impersonación activa.
    """
    return user and user.is_superuser and is_admin_path(request_path) and not is_impersonating


def is_admin_path(path: str) -> bool:
    """Verifica si el path es parte del admin de Django."""
    return str(path).startswith("/admin/")

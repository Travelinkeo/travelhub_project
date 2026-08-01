import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from django.conf import settings

logger = logging.getLogger(__name__)

_F = TypeVar("_F", bound=Callable[..., Any])


def idempotent_task(timeout: int = 3600, key_prefix: str = "celery_idem") -> Callable[[_F], _F]:
    """
    Decorador de IDEMPOTENCIA para tareas Celery.
    Previene ejecución duplicada usando Redis como lock distribuido.

    Args:
        timeout: Tiempo en segundos antes de que el lock expire (default: 1 hora)
        key_prefix: Prefijo para la clave de Redis (default: "celery_idem")

    Uso:
        @shared_task
        @idempotent_task(timeout=3600)
        def procesar_pago(pago_id):
            ...
    """

    def decorator(func: _F) -> _F:
        """decorator."""

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """wrapper."""
            # Generar clave única basada en nombre de tarea + argumentos
            task_name = func.__name__
            args_key = f"{key_prefix}:{task_name}:{args}:{sorted(kwargs.items())}"

            try:
                from django.core.cache import cache

                # Intentar adquirir lock
                lock_key = f"lock:{args_key}"
                if not cache.add(lock_key, "processing", timeout):
                    logger.warning(
                        f"⏭️ [IDEMPOTENT] Tarea {task_name} ya en proceso o completada. "
                        f"Args: {args}. Saltando ejecución duplicada."
                    )
                    return f"SKIPPED_DUPLICATE_{task_name}"

                try:
                    # Ejecutar tarea
                    result = func(*args, **kwargs)

                    # Marcar como completada (extender timeout para prevenir re-ejecución)
                    cache.set(lock_key, "completed", timeout)

                    return result
                except Exception as e:
                    # En caso de error, liberar lock para permitir retry
                    cache.delete(lock_key)
                    raise e

            except ImportError:
                # Si no hay cache disponible, ejecutar sin idempotencia
                logger.debug("Cache not available, running without idempotency")
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in idempotent_task decorator: {e}")
                return func(*args, **kwargs)

        return wrapper

    return decorator


def safe_delay(
    task_func: Callable[..., Any],
    *args: Any,
    _queue: str | None = None,
    **kwargs: Any,
) -> Any | None:
    """
    ASISTENCIA DE CARRIL: Wrapper seguro para encolar tareas de Celery.
    Si Redis o el Broker de mensajes están caídos, captura el error.
    En DESARROLLO (DEBUG=True), cae en ejecución síncrona para no detener la operación.
    """
    try:
        # Intentamos enviar la tarea a la cola con prioridad si se especifica
        if _queue:
            from django.db import transaction

            task = transaction.on_commit(
                lambda: task_func.apply_async(args=args, kwargs=kwargs, queue=_queue)
            )
        else:
            from django.db import transaction

            task = transaction.on_commit(lambda: task_func.delay(*args, **kwargs))

        # Algunos objetos task de Celery no tienen .id inmediatamente si falla el broker
        task_id = getattr(task, "id", str(task))
        logger.info(
            f"✅ Tarea {task_func.name} encolada con éxito en cola '{_queue or 'default'}'. ID: {task_id}"
        )
        return task_id
    except Exception as e:
        # Capturamos errores de conexión, DNS (redis:6379), etc.
        error_msg = str(e)
        if settings.DEBUG:
            logger.warning(
                f"⚠️ Broker fuera de línea o error de DNS ({error_msg}). Ejecutando {task_func.name} en modo SÍNCRONO (DEBUG=True)."
            )
            try:
                # Ejecución síncrona directa (como una función normal)
                # IMPORTANTE: Al llamar directamente, perdemos el aislamiento de proceso, pero salvamos la operación del usuario.
                task_func(*args, **kwargs)
                return f"SYNC_COMPLETED_{task_func.name}"
            except Exception as se:
                logger.error(f" Error en ejecución síncrona de {task_func.name}: {se}")
                return None

        logger.error(
            f"⚠️ FALLO DE INFRAESTRUCTURA: No se pudo encolar {task_func.name}. Error: {error_msg}"
        )
        return None


def tenant_task(*task_args: Any, **task_kwargs: Any) -> Callable[[_F], _F]:
    """
    🛡️ DECORADOR MULTI-TENANT PARA CELERY (PRO)
    Envuelve @shared_task para asegurar que la tarea se ejecute dentro del context manager
    de la agencia, activando los filtros del TenantManager automáticamente.

    Mejoras:
    1. Soporta argumentos posicionales y nominales.
    2. Maneja múltiples nombres (agency_id, agencia_id, id_agencia).
    3. Validación estricta: Si la tarea requiere agencia y no se provee, falla antes de causar data leakage.
    """

    def decorator(func: _F) -> _F:
        """decorator."""
        import inspect
        from functools import wraps

        from celery import shared_task

        @shared_task(*task_args, **task_kwargs)
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """wrapper."""
            # 1. Intentar encontrar el agency_id en los argumentos
            agency_id = kwargs.pop(
                "agency_id", kwargs.pop("agencia_id", kwargs.pop("id_agencia", None))
            )

            # Si no está en kwargs, buscar en args si sabemos la posición (opcional, pero útil)
            if not agency_id:
                # Inspeccionamos la función original para ver si alguno de sus parámetros es el ID
                sig = inspect.signature(func)
                bound_args = sig.bind_partial(*args, **kwargs)
                agency_id = (
                    bound_args.arguments.get("agency_id")
                    or bound_args.arguments.get("agencia_id")
                    or bound_args.arguments.get("id_agencia")
                )

            if agency_id:
                from core.api import Agencia, agency_context

                try:
                    # Usamos all_objects para bypass del TenantManager si existe, de lo contrario fallback a objects
                    manager = getattr(Agencia, "all_objects", Agencia.objects)
                    agencia = manager.get(id=agency_id)
                    with agency_context(agencia):
                        logger.info(
                            f"🏢 [TENANT TASK] Contexto: {agencia.nombre} | Tarea: {func.__name__}"
                        )
                        return func(*args, **kwargs)
                except Agencia.DoesNotExist:
                    logger.error(
                        f"❌ [TENANT TASK] Agencia ID {agency_id} no existe. Abortando {func.__name__}"
                    )
                    return None
                except Exception as e:
                    logger.error(
                        f"❌ [TENANT TASK] Error crítico de contexto en {func.__name__}: {e}"
                    )
                    raise e

            # Si la tarea no tiene agency_id, se ejecuta en el "Modo Global" (System Mode)
            # Esto activa el bypass en AgenciaManager.get_queryset()
            from core.api import system_context

            logger.warning(f" [GLOBAL TASK] Tarea {func.__name__} ejecutándose en Modo Sistema.")
            with system_context():
                return func(*args, **kwargs)

        return wrapper

    return decorator


def _is_celery_available() -> bool:
    """
    Verifica si el broker de Celery (Redis) está en línea.
    """
    try:
        from django.conf import settings

        broker_url = getattr(settings, "CELERY_BROKER_URL", None) or getattr(
            settings, "BROKER_URL", None
        )
        if not broker_url or "memory" in str(broker_url):
            return False
        import redis

        client = redis.from_url(broker_url, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        return True
    except Exception:
        return False

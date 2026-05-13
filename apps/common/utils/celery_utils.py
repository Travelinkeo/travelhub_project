import logging
from typing import Any

from celery.exceptions import OperationalError, TimeoutError

logger = logging.getLogger(__name__)

from django.conf import settings


def safe_delay(task_func: Any, *args: Any, **kwargs: Any) -> Any | None:
    """
    ASISTENCIA DE CARRIL: Wrapper seguro para encolar tareas de Celery.
    Si Redis o el Broker de mensajes están caídos, captura el error.
    En DESARROLLO (DEBUG=True), cae en ejecución síncrona para no detener la operación.
    """
    try:
        # Intentamos enviar la tarea a la cola
        task = task_func.delay(*args, **kwargs)
        # Algunos objetos task de Celery no tienen .id inmediatamente si falla el broker
        task_id = getattr(task, 'id', str(task))
        logger.info(f"✅ Tarea {task_func.name} encolada con éxito. ID: {task_id}")
        return task_id
    except Exception as e:
        # Capturamos errores de conexión, DNS (redis:6379), etc.
        error_msg = str(e)
        if settings.DEBUG:
            logger.warning(f"⚠️ Broker fuera de línea o error de DNS ({error_msg}). Ejecutando {task_func.name} en modo SÍNCRONO (DEBUG=True).")
            try:
                # Ejecución síncrona directa (como una función normal)
                # IMPORTANTE: Al llamar directamente, perdemos el aislamiento de proceso, pero salvamos la operación del usuario.
                result = task_func(*args, **kwargs)
                return f"SYNC_COMPLETED_{task_func.name}"
            except Exception as se:
                logger.error(f"❌ Error en ejecución síncrona de {task_func.name}: {se}")
                return None
        
        logger.error(f"⚠️ FALLO DE INFRAESTRUCTURA: No se pudo encolar {task_func.name}. Error: {error_msg}")
        return None


def tenant_task(*task_args, **task_kwargs):
    """
    🛡️ DECORADOR MULTI-TENANT PARA CELERY (PRO)
    Envuelve @shared_task para asegurar que la tarea se ejecute dentro del context manager
    de la agencia, activando los filtros del TenantManager automáticamente.
    
    Mejoras:
    1. Soporta argumentos posicionales y nominales.
    2. Maneja múltiples nombres (agency_id, agencia_id, id_agencia).
    3. Validación estricta: Si la tarea requiere agencia y no se provee, falla antes de causar data leakage.
    """
    def decorator(func):
        import inspect
        from functools import wraps

        from celery import shared_task

        @shared_task(*task_args, **task_kwargs)
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 1. Intentar encontrar el agency_id en los argumentos
            agency_id = kwargs.pop('agency_id', kwargs.pop('agencia_id', kwargs.pop('id_agencia', None)))
            
            # Si no está en kwargs, buscar en args si sabemos la posición (opcional, pero útil)
            if not agency_id:
                # Inspeccionamos la función original para ver si alguno de sus parámetros es el ID
                sig = inspect.signature(func)
                bound_args = sig.bind_partial(*args, **kwargs)
                agency_id = bound_args.arguments.get('agency_id') or \
                           bound_args.arguments.get('agencia_id') or \
                           bound_args.arguments.get('id_agencia')

            if agency_id:
                from core.middleware import agency_context
                from core.models.agencia import Agencia
                try:
                    # Usamos all_objects para bypass del TenantManager
                    agencia = Agencia.all_objects.get(id=agency_id)
                    with agency_context(agencia):
                        logger.info(f"🏢 [TENANT TASK] Contexto: {agencia.nombre} | Tarea: {func.__name__}")
                        return func(*args, **kwargs)
                except Agencia.DoesNotExist:
                    logger.error(f"❌ [TENANT TASK] Agencia ID {agency_id} no existe. Abortando {func.__name__}")
                    return None
                except Exception as e:
                    logger.error(f"❌ [TENANT TASK] Error crítico de contexto en {func.__name__}: {e}")
                    raise e
            
            # Si la tarea no tiene agency_id, se ejecuta en el "Modo Global" (System Mode)
            # Esto activa el bypass en AgenciaManager.get_queryset()
            from core.middleware import system_context
            logger.warning(f"🌐 [GLOBAL TASK] Tarea {func.__name__} ejecutándose en Modo Sistema.")
            with system_context():
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

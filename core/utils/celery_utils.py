import logging
from typing import Any, Optional
from celery.exceptions import TimeoutError, OperationalError

logger = logging.getLogger(__name__)

from django.conf import settings

def safe_delay(task_func: Any, *args: Any, **kwargs: Any) -> Optional[Any]:
    """
    ASISTENCIA DE CARRIL: Wrapper seguro para encolar tareas de Celery.
    Si Redis o el Broker de mensajes están caídos, captura el error.
    En DESARROLLO (DEBUG=True), cae en ejecución síncrona para no detener la operación.
    """
    try:
        # Intentamos enviar la tarea a la cola
        task = task_func.delay(*args, **kwargs)
        logger.info(f"✅ Tarea {task_func.name} encolada con éxito. ID: {task.id}")
        return task.id
    except (OperationalError, TimeoutError, ConnectionError, Exception) as e:
        if settings.DEBUG:
            logger.warning(f"⚠️ Broker fuera de línea. Ejecutando {task_func.name} en modo SÍNCRONO (DEBUG=True).")
            try:
                # Ejecución síncrona directa (como una función normal)
                result = task_func(*args, **kwargs)
                # Simulamos un TaskID para que el frontend no rompa
                return "SYNC_TASK_COMPLETED"
            except Exception as se:
                logger.error(f"❌ Error en ejecución síncrona de {task_func.name}: {se}")
                return None
        
        logger.error(f"⚠️ FALLO DE INFRAESTRUCTURA: No se pudo encolar {task_func.name}. Error: {e}")
        return None

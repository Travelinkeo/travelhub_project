import logging
import os

from celery import Celery
from django.conf import settings  # Importar settings
from kombu import Exchange, Queue

logger = logging.getLogger(__name__)

# Configurar Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")

app = Celery("travelhub")

# Cargar configuración desde Django settings con prefijo CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# ==========================================
# 🧠 ARQUITECTURA DE COLAS (QUEUE ROUTING)
# ==========================================

# Definimos los "carriles" por donde viajarán las tareas
app.conf.task_queues = (
    Queue("default", Exchange("default"), routing_key="default"),
    # 🏎️ CARRIL RÁPIDO: Tareas IA que el usuario está esperando en pantalla (< 5 segs)
    Queue("ia_fast", Exchange("ia_fast"), routing_key="ia_fast"),
    # 🐢 CARRIL PESADO: Tareas masivas de IA que corren en segundo plano (> 1 min)
    Queue("ia_heavy", Exchange("ia_heavy"), routing_key="ia_heavy"),
    # 📱 CARRIL NOTIFICACIONES: WhatsApp y Correos (Aislado para que nunca se retrase)
    Queue("notifications", Exchange("notifications"), routing_key="notifications"),
)

# default exchange/queue
app.conf.task_default_queue = "default"
app.conf.task_default_exchange = "default"
app.conf.task_default_routing_key = "default"

# ==========================================
# 🚦 ENRUTADOR AUTOMÁTICO DE TAREAS
# ==========================================
# Nota: Las rutas se definen en settings.CELERY_TASK_ROUTES para centralizar.
# Anteriormente se definian aqui, pero app.conf.task_routes sobreescribe
# las rutas de settings, causando conflictos. Ahora solo se usa settings.

# Auto-descubrir tareas en todas las apps
app.autodiscover_tasks()
app.autodiscover_tasks(packages=["apps.finance"], related_name="tasks_tax_refund")  # noqa: F811

# ==========================================


# Cargar CELERY_BEAT_SCHEDULE desde settings o desde el módulo dedicado (fallback seguro)
# Usamos getattr para evitar AttributeError si el settings.py no tiene la variable
_beat_schedule = getattr(settings, "CELERY_BEAT_SCHEDULE", None)
if _beat_schedule is None:
    try:
        from travelhub.celery_beat_schedule import CELERY_BEAT_SCHEDULE as _beat_schedule

        logger.info("✅ CELERY_BEAT_SCHEDULE cargado desde celery_beat_schedule.py")
    except ImportError:
        _beat_schedule = {}
        logger.warning(
            "⚠️ No se encontró CELERY_BEAT_SCHEDULE. Celery Beat no tendrá tareas programadas."
        )

app.conf.beat_schedule = _beat_schedule


@app.task(bind=True, ignore_result=True, time_limit=30, soft_time_limit=20)
def debug_task(self):
    logger.debug(f"Request: {self.request!r}")


# ==========================================
# 🚨 ALERTAS: FALLOS DE TAREAS → SENTRY
# ==========================================

from celery.signals import task_failure, task_retry  # noqa: E402


@task_failure.connect
def handle_task_failure(sender, task_id, exception, args, kwargs, traceback, einfo, **kw):
    """Captura fallos de tareas Celery y los reporta a Sentry con contexto completo."""
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            scope.set_tag("celery.task_name", sender.name)
            scope.set_tag("celery.task_id", task_id)
            scope.set_extra("celery.args", str(args)[:500])
            scope.set_extra("celery.kwargs", str(kwargs)[:500])
            sentry_sdk.capture_exception(exception)
            logger.error(
                "❌ Celery task failed: %s [%s] — %s",
                sender.name,
                task_id,
                exception,
            )
    except ImportError:
        logger.error("Task %s failed: %s", sender.name, exception)


@task_retry.connect
def handle_task_retry(sender, reason, **kw):
    """Loggea reintentos de tareas para debugging."""
    logger.warning("⚠️ Celery task retry: %s — reason: %s", sender.name, reason)

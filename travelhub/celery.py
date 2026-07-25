"""Configuración de Celery para TravelHub — define colas, rutas, beat schedule y manejadores de fallos."""

import logging
import os

from celery import Celery
from kombu import Exchange, Queue

logger = logging.getLogger(__name__)

# Configura Django settings (development por defecto local, production en server real)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings.development")

# Crea la instancia de Celery
app = Celery("travelhub")

# Carga configuración desde Django settings con prefijo CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# ==========================================
# 🧠 ARQUITECTURA DE COLAS (QUEUE ROUTING)
# ==========================================
# Optimizado Fase 5: de 4 colas a 2.
#
#   Queue       │ Uso                                         │ Workers
#   ────────────┼─────────────────────────────────────────────┼────────
#   celery      │ Tareas generales + IA pesada + IA rápida   │ 2-4
#   notifications│ WhatsApp, Telegram, Email (aislado)         │ 1-2
#
# ❌ Eliminadas: ia_fast (se unifica a celery), ia_heavy (se unifica a celery)
# La separación de notifications evita que notificaciones urgentes (cobranza,
# confirmación de pago) se bloqueen detrás de tareas batch pesadas.

# Define las colas disponibles (2 colas optimizadas Fase 5)
app.conf.task_queues = (
    Queue("celery", Exchange("celery"), routing_key="celery"),
    Queue("notifications", Exchange("notifications"), routing_key="notifications"),
)

# Configura la cola por defecto
app.conf.task_default_queue = "celery"
app.conf.task_default_exchange = "celery"
app.conf.task_default_routing_key = "celery"

# ==========================================
# 🚦 ENRUTADOR AUTOMÁTICO DE TAREAS
# ==========================================
# Nota: Las rutas se definen en settings.CELERY_TASK_ROUTES para centralizar.
# Anteriormente se definian aqui, pero app.conf.task_routes sobreescribe
# las rutas de settings, causando conflictos. Ahora solo se usa settings.

# Auto-descubre tareas registradas en apps y apps.finance
app.autodiscover_tasks(packages=["apps", "apps.finance"])

# ==========================================


# Carga CELERY_BEAT_SCHEDULE con import diferido para evitar AppRegistryNotReady
_beat_schedule = None
try:
    from django.conf import settings as _dj_settings

    _beat_schedule = getattr(_dj_settings, "CELERY_BEAT_SCHEDULE", None)
except Exception as e:
    logger.debug(f"Django no esta configurado aun; usamos fallback: {e}")

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
    """Tarea de depuración — loggea el request de la tarea para verificar que Celery funciona."""
    logger.debug(f"Request: {self.request!r}")


# ==========================================
# 🚨 ALERTAS: FALLOS DE TAREAS → SENTRY
# ==========================================

from celery.signals import task_failure, task_retry  # noqa: E402


@task_failure.connect
def handle_task_failure(sender, task_id, exception, args, kwargs, traceback, einfo, **kw):
    """Captura fallos de tareas Celery y los reporta a Sentry con contexto completo. Args: sender (Task), task_id (str), exception (Exception)."""
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
    """Loggea reintentos de tareas para debugging. Args: sender (Task), reason (str)."""
    logger.warning("⚠️ Celery task retry: %s — reason: %s", sender.name, reason)

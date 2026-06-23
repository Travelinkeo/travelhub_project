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
# Le decimos a Celery a qué carril mandar cada tarea automáticamente

app.conf.task_routes = {
    # -- IA MULTIMODAL (ALTA PRIORIDAD) --
    # Tareas que el usuario espera en tiempo real
    "core.tasks.procesar_pasaporte_ocr": {"queue": "ia_fast"},
    "core.tasks.procesar_nota_voz": {"queue": "ia_fast"},
    "core.tasks.parsear_boleto_individual": {"queue": "ia_fast"},
    # -- IA FINANCIERA MASIVA (BAJA PRIORIDAD) --
    # Procesar conciliaciones pesadas se va por el carril pesado
    "apps.finance.tasks_reconciliation.conciliar_reporte_batch_task": {"queue": "ia_heavy"},
    # -- NOTIFICACIONES Y COMUNICACIÓN --
    # Aislado para que los correos/whatsapps fluyan sin bloqueos
    "core.tasks.enviar_notificacion_whatsapp_task": {"queue": "notifications"},
}


# Auto-descubrir tareas en todas las apps
app.autodiscover_tasks()

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

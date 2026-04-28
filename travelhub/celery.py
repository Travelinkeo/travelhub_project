
import os
from celery import Celery
from kombu import Queue, Exchange

# Configurar Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')

app = Celery('travelhub')

# Cargar configuración desde Django settings con prefijo CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# ==========================================
# 🧠 ARQUITECTURA DE COLAS (QUEUE ROUTING)
# ==========================================

# Definimos los "carriles" por donde viajarán las tareas
app.conf.task_queues = (
    Queue('default', Exchange('default'), routing_key='default'),
    
    # 🏎️ CARRIL RÁPIDO: Tareas IA que el usuario está esperando en pantalla (< 5 segs)
    Queue('ia_fast', Exchange('ia_fast'), routing_key='ia_fast'),
    
    # 🐢 CARRIL PESADO: Tareas masivas de IA que corren en segundo plano (> 1 min)
    Queue('ia_heavy', Exchange('ia_heavy'), routing_key='ia_heavy'),
    
    # 📱 CARRIL NOTIFICACIONES: WhatsApp y Correos (Aislado para que nunca se retrase)
    Queue('notifications', Exchange('notifications'), routing_key='notifications'),
)

# default exchange/queue
app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'default'
app.conf.task_default_routing_key = 'default'

# ==========================================
# 🚦 ENRUTADOR AUTOMÁTICO DE TAREAS
# ==========================================
# Le decimos a Celery a qué carril mandar cada tarea automáticamente

app.conf.task_routes = {
    # -- IA MULTIMODAL (ALTA PRIORIDAD) --
    # Tareas que el usuario espera en tiempo real
    'core.tasks.procesar_pasaporte_ocr': {'queue': 'ia_fast'},
    'core.tasks.procesar_nota_voz': {'queue': 'ia_fast'},
    'core.tasks.parsear_boleto_individual': {'queue': 'ia_fast'},
    
    # -- IA FINANCIERA MASIVA (BAJA PRIORIDAD) --
    # Procesar conciliaciones pesadas se va por el carril pesado
    'finance.tasks_reconciliation.conciliar_reporte_batch_task': {'queue': 'ia_heavy'},
    
    # -- NOTIFICACIONES Y COMUNICACIÓN --
    # Aislado para que los correos/whatsapps fluyan sin bloqueos
    'core.tasks.enviar_notificacion_whatsapp_task': {'queue': 'notifications'},
}

# Auto-descubrir tareas en todas las apps
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

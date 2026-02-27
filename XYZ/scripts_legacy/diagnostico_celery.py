"""
Script de diagnóstico para Celery en producción
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from celery import Celery
from django.conf import settings

print("=" * 60)
print("DIAGNÓSTICO DE CELERY")
print("=" * 60)

# 1. Verificar configuración
print("\n1. CONFIGURACIÓN:")
print(f"   CELERY_BROKER_URL: {settings.CELERY_BROKER_URL[:30]}...")
print(f"   CELERY_RESULT_BACKEND: {settings.CELERY_RESULT_BACKEND[:30]}...")

# 2. Verificar variables de entorno
print("\n2. VARIABLES DE ENTORNO:")
env_vars = ['GMAIL_USER', 'GMAIL_APP_PASSWORD', 'EMAIL_HOST_USER', 'REDIS_URL']
for var in env_vars:
    value = os.getenv(var)
    if value:
        print(f"   ✅ {var}: {'*' * 10}")
    else:
        print(f"   ❌ {var}: NO CONFIGURADA")

# 3. Verificar conexión Redis
print("\n3. CONEXIÓN REDIS:")
try:
    from redis import Redis
    redis_url = settings.CELERY_BROKER_URL
    r = Redis.from_url(redis_url)
    r.ping()
    print("   ✅ Redis conectado")
except Exception as e:
    print(f"   ❌ Redis error: {e}")

# 4. Verificar tareas registradas
print("\n4. TAREAS REGISTRADAS:")
app = Celery('travelhub')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

for task_name in sorted(app.tasks.keys()):
    if not task_name.startswith('celery.'):
        print(f"   - {task_name}")

# 5. Verificar schedule
print("\n5. TAREAS PROGRAMADAS:")
from travelhub.celery_beat_schedule import CELERY_BEAT_SCHEDULE
for name, config in CELERY_BEAT_SCHEDULE.items():
    print(f"   - {name}: {config['task']}")
    print(f"     Schedule: {config['schedule']}")

print("\n" + "=" * 60)
print("DIAGNÓSTICO COMPLETADO")
print("=" * 60)

# core/api/tasks.py
"""
Celery tasks para el sistema de webhooks.
"""

from .webhook_dispatcher import send_webhook_task  # noqa: F401

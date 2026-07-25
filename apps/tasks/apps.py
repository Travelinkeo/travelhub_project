"""Configuración de la aplicación Django tasks.
"""

from django.apps import AppConfig


class TasksConfig:
    """Configuración de tasks. Uso: instanciar según necesidad del dominio.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tasks"
    verbose_name = "Tareas"

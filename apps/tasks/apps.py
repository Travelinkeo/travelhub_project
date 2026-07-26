from django.apps import AppConfig


class TasksConfig(AppConfig):
    """TasksConfig."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tasks"
    verbose_name = "Tareas"

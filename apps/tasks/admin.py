"""Configuración del panel de administración para tasks.
"""

from django.contrib import admin

from core.api import SaaSAdminMixin

from .models import ComentarioTarea, Tarea


@admin.register(Tarea)
class TareaAdmin:
    """Configuración de administración para tarea. Uso: instanciar según necesidad del dominio.
    """
    list_display = ["titulo", "estado", "prioridad", "asignado_a", "fecha_vencimiento"]
    list_filter = ["estado", "prioridad"]
    search_fields = ["titulo", "descripcion"]


@admin.register(ComentarioTarea)
class ComentarioTareaAdmin:
    """Configuración de administración para comentariotarea. Uso: instanciar según necesidad del dominio.
    """
    list_display = ["tarea", "usuario", "created_at"]

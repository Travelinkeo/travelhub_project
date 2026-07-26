from django.contrib import admin

from core.api import SaaSAdminMixin

from .models import ComentarioTarea, Tarea


@admin.register(Tarea)
class TareaAdmin(SaaSAdminMixin, admin.ModelAdmin):
    """TareaAdmin."""

    list_display = ["titulo", "estado", "prioridad", "asignado_a", "fecha_vencimiento"]
    list_filter = ["estado", "prioridad"]
    search_fields = ["titulo", "descripcion"]


@admin.register(ComentarioTarea)
class ComentarioTareaAdmin(SaaSAdminMixin, admin.ModelAdmin):
    """ComentarioTareaAdmin."""

    list_display = ["tarea", "usuario", "created_at"]

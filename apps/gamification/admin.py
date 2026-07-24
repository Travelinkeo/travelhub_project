from django.contrib import admin

from core.api import SaaSAdminMixin

from .models import Logro, LogroProgreso, Nivel, PuntuacionUsuario


@admin.register(Nivel)
class NivelAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ["nombre", "puntos_minimos", "icono", "color"]
    ordering = ["puntos_minimos"]


@admin.register(Logro)
class LogroAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ["codigo", "nombre", "categoria", "puntos", "activo"]
    list_filter = ["categoria", "activo"]
    search_fields = ["nombre", "codigo"]
    prepopulated_fields = {"codigo": ("nombre",)}


@admin.register(LogroProgreso)
class LogroProgresoAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ["usuario", "logro", "progreso", "completado", "fecha_completado"]
    list_filter = ["completado"]
    search_fields = ["usuario__email", "logro__nombre"]


@admin.register(PuntuacionUsuario)
class PuntuacionUsuarioAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ["usuario", "puntos_total", "nivel", "logros_completados"]
    ordering = ["-puntos_total"]

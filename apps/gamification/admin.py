from django.contrib import admin

from .models import Logro, LogroProgreso, Nivel, PuntuacionUsuario


@admin.register(Nivel)
class NivelAdmin(admin.ModelAdmin):
    list_display = ["nombre", "puntos_minimos", "icono", "color"]
    ordering = ["puntos_minimos"]


@admin.register(Logro)
class LogroAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nombre", "categoria", "puntos", "activo"]
    list_filter = ["categoria", "activo"]
    search_fields = ["nombre", "codigo"]
    prepopulated_fields = {"codigo": ("nombre",)}


@admin.register(LogroProgreso)
class LogroProgresoAdmin(admin.ModelAdmin):
    list_display = ["usuario", "logro", "progreso", "completado", "fecha_completado"]
    list_filter = ["completado"]
    search_fields = ["usuario__email", "logro__nombre"]


@admin.register(PuntuacionUsuario)
class PuntuacionUsuarioAdmin(admin.ModelAdmin):
    list_display = ["usuario", "puntos_total", "nivel", "logros_completados"]
    ordering = ["-puntos_total"]

"""Configuración del panel de administración para contabilidad.
"""

from django.contrib import admin

from core.api import SaaSAdminMixin

from .models import AsientoContable, CuentaContable, MovimientoContable


class MovimientoContableInline:
    """Clase MovimientoContableInline. Uso: según contexto de la aplicación.
    """
    model = MovimientoContable
    extra = 2
    fields = ("cuenta", "tipo", "monto_ves", "monto_usd")


@admin.register(CuentaContable)
class CuentaContableAdmin:
    """Configuración de administración para cuentacontable. Uso: instanciar según necesidad del dominio.
    """
    list_display = ("codigo", "nombre", "tipo", "cuenta_padre", "acepta_movimientos")
    list_filter = ("tipo", "acepta_movimientos")
    search_fields = ("codigo", "nombre")
    ordering = ("codigo",)

    fieldsets = (
        ("Información Básica", {"fields": ("codigo", "nombre", "tipo")}),
        ("Jerarquía", {"fields": ("cuenta_padre", "acepta_movimientos")}),
    )


@admin.register(AsientoContable)
class AsientoContableAdmin:
    """Configuración de administración para asientocontable. Uso: instanciar según necesidad del dominio.
    """
    list_display = ("id", "fecha_contable", "glosa", "content_object")
    list_filter = ("fecha_contable",)
    search_fields = ("glosa",)
    date_hierarchy = "fecha_contable"
    ordering = ("-fecha_contable",)

    inlines = [MovimientoContableInline]

    fieldsets = (
        ("Información del Asiento", {"fields": ("fecha_contable", "glosa")}),
        ("Documento Origen", {"fields": ("content_type", "object_id")}),
    )


admin.site.register(MovimientoContable)

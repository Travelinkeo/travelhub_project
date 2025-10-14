# contabilidad/admin.py
"""
Configuración del admin para el módulo de contabilidad.
Incluye gestión de Plan de Cuentas, Asientos Contables y Tasas BCV.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import PlanContable, AsientoContable, DetalleAsiento, TasaCambioBCV


class DetalleAsientoInline(admin.TabularInline):
    model = DetalleAsiento
    extra = 2
    fields = ('linea', 'cuenta_contable', 'debe', 'haber', 'debe_bsd', 'haber_bsd', 'descripcion_linea')
    readonly_fields = ()


@admin.register(PlanContable)
class PlanContableAdmin(admin.ModelAdmin):
    list_display = ('codigo_cuenta', 'nombre_cuenta', 'tipo_cuenta', 'naturaleza', 'permite_movimientos', 'nivel')
    list_filter = ('tipo_cuenta', 'naturaleza', 'permite_movimientos', 'nivel')
    search_fields = ('codigo_cuenta', 'nombre_cuenta')
    ordering = ('codigo_cuenta',)
    
    fieldsets = (
        (_('Información Básica'), {
            'fields': ('codigo_cuenta', 'nombre_cuenta', 'tipo_cuenta')
        }),
        (_('Jerarquía'), {
            'fields': ('nivel', 'cuenta_padre', 'permite_movimientos')
        }),
        (_('Características'), {
            'fields': ('naturaleza', 'descripcion')
        }),
    )


@admin.register(AsientoContable)
class AsientoContableAdmin(admin.ModelAdmin):
    list_display = ('numero_asiento', 'fecha_contable', 'tipo_asiento', 'descripcion_general', 
                    'total_debe', 'total_haber', 'estado', 'esta_cuadrado_display')
    list_filter = ('tipo_asiento', 'estado', 'fecha_contable')
    search_fields = ('numero_asiento', 'descripcion_general', 'referencia_documento')
    date_hierarchy = 'fecha_contable'
    ordering = ('-fecha_contable', '-numero_asiento')
    readonly_fields = ('total_debe', 'total_haber', 'fecha_creacion', 'esta_cuadrado_display')
    
    inlines = [DetalleAsientoInline]
    
    fieldsets = (
        (_('Información del Asiento'), {
            'fields': ('numero_asiento', 'fecha_contable', 'tipo_asiento', 'estado')
        }),
        (_('Descripción'), {
            'fields': ('descripcion_general', 'referencia_documento')
        }),
        (_('Moneda y Tasa'), {
            'fields': ('moneda', 'tasa_cambio_aplicada')
        }),
        (_('Totales'), {
            'fields': ('total_debe', 'total_haber', 'esta_cuadrado_display'),
            'classes': ('collapse',)
        }),
        (_('Auditoría'), {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',)
        }),
    )
    
    def esta_cuadrado_display(self, obj):
        if obj.esta_cuadrado:
            return format_html('<span style="color: green;">✓ Cuadrado</span>')
        return format_html('<span style="color: red;">✗ Descuadrado</span>')
    esta_cuadrado_display.short_description = _('Estado Balance')
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.calcular_totales()


@admin.register(TasaCambioBCV)
class TasaCambioBCVAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'tasa_bsd_por_usd', 'fuente', 'actualizado')
    list_filter = ('fuente', 'fecha')
    search_fields = ('fecha',)
    date_hierarchy = 'fecha'
    ordering = ('-fecha',)
    readonly_fields = ('creado', 'actualizado')
    
    fieldsets = (
        (_('Tasa de Cambio'), {
            'fields': ('fecha', 'tasa_bsd_por_usd', 'fuente')
        }),
        (_('Auditoría'), {
            'fields': ('creado', 'actualizado'),
            'classes': ('collapse',)
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        # Prevenir eliminación accidental de tasas históricas
        return request.user.is_superuser

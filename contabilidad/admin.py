from django.contrib import admin
from .models import PlanContable, AsientoContable, DetalleAsiento

class DetalleAsientoInline(admin.TabularInline):
    model = DetalleAsiento
    extra = 2
    autocomplete_fields = ['cuenta_contable']

@admin.register(AsientoContable)
class AsientoContableAdmin(admin.ModelAdmin):
    list_display = ('numero_asiento', 'fecha_contable', 'descripcion_general', 'tipo_asiento', 'estado', 'esta_cuadrado')
    search_fields = ('numero_asiento', 'descripcion_general', 'referencia_documento')
    list_filter = ('estado', 'tipo_asiento', 'fecha_contable')
    inlines = [DetalleAsientoInline]
    readonly_fields = ('total_debe', 'total_haber')

@admin.register(PlanContable)
class PlanContableAdmin(admin.ModelAdmin):
    list_display = ('codigo_cuenta', 'nombre_cuenta', 'tipo_cuenta', 'naturaleza', 'permite_movimientos')
    search_fields = ('codigo_cuenta', 'nombre_cuenta')
    list_filter = ('tipo_cuenta', 'naturaleza', 'permite_movimientos')
    autocomplete_fields = ['cuenta_padre']

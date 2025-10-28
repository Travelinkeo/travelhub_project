# core/admin/retenciones_admin.py
"""Admin para Retenciones ISLR"""
from django.contrib import admin
from django.utils.html import format_html
from core.models.retenciones_islr import RetencionISLR


@admin.register(RetencionISLR)
class RetencionISLRAdmin(admin.ModelAdmin):
    """Admin para retenciones ISLR"""
    
    list_display = [
        'numero_comprobante', 'fecha_emision', 'cliente', 'factura',
        'base_imponible', 'porcentaje_retencion', 'monto_retenido',
        'estado', 'periodo_fiscal'
    ]
    
    list_filter = ['estado', 'tipo_operacion', 'periodo_fiscal', 'fecha_emision']
    
    search_fields = [
        'numero_comprobante', 'cliente__nombres', 'cliente__apellidos',
        'factura__numero_factura', 'observaciones'
    ]
    
    readonly_fields = ['monto_retenido', 'creado', 'actualizado']
    
    autocomplete_fields = ['factura', 'cliente']
    
    fieldsets = [
        ('Información Básica', {
            'fields': ['numero_comprobante', 'fecha_emision', 'fecha_operacion', 'periodo_fiscal']
        }),
        ('Relaciones', {
            'fields': ['factura', 'cliente']
        }),
        ('Tipo de Operación', {
            'fields': ['tipo_operacion', 'codigo_concepto']
        }),
        ('Montos', {
            'fields': ['base_imponible', 'porcentaje_retencion', 'monto_retenido']
        }),
        ('Estado y Archivo', {
            'fields': ['estado', 'archivo_comprobante']
        }),
        ('Observaciones', {
            'fields': ['observaciones'],
            'classes': ['collapse']
        }),
        ('Auditoría', {
            'fields': ['creado', 'actualizado'],
            'classes': ['collapse']
        })
    ]
    
    actions = ['marcar_como_aplicada', 'exportar_reporte']
    
    def marcar_como_aplicada(self, request, queryset):
        """Marcar retenciones como aplicadas en declaración"""
        updated = queryset.update(estado='APL')
        self.message_user(request, f'{updated} retención(es) marcada(s) como aplicada(s).')
    marcar_como_aplicada.short_description = 'Marcar como aplicada en declaración'
    
    def exportar_reporte(self, request, queryset):
        """Exportar reporte de retenciones"""
        # TODO: Implementar exportación
        self.message_user(request, 'Exportación pendiente de implementación.')
    exportar_reporte.short_description = 'Exportar reporte de retenciones'

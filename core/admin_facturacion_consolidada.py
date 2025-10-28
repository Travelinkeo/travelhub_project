# core/admin_facturacion_consolidada.py
"""
Admin para modelos consolidados de facturación
"""
from django.contrib import admin
from .models.facturacion_consolidada import FacturaConsolidada, ItemFacturaConsolidada, DocumentoExportacionConsolidado


class ItemFacturaConsolidadaInline(admin.TabularInline):
    model = ItemFacturaConsolidada
    extra = 1
    fields = ('descripcion', 'cantidad', 'precio_unitario', 'tipo_servicio', 'es_gravado', 'alicuota_iva')


class DocumentoExportacionConsolidadoInline(admin.TabularInline):
    model = DocumentoExportacionConsolidado
    extra = 0
    fields = ('tipo_documento', 'numero_documento', 'archivo')


@admin.register(FacturaConsolidada)
class FacturaConsolidadaAdmin(admin.ModelAdmin):
    list_display = ('numero_factura', 'cliente', 'fecha_emision', 'tipo_operacion', 'moneda_operacion', 
                   'monto_total', 'estado')
    list_filter = ('estado', 'tipo_operacion', 'moneda_operacion', 'cliente_es_residente', 'fecha_emision')
    search_fields = ('numero_factura', 'numero_control', 'cliente__nombre', 'cliente__apellido')
    readonly_fields = ('subtotal', 'monto_total', 'saldo_pendiente')
    inlines = [ItemFacturaConsolidadaInline, DocumentoExportacionConsolidadoInline]
    
    fieldsets = (
        ('Identificación', {
            'fields': ('numero_factura', 'numero_control', 'venta_asociada')
        }),
        ('Cliente', {
            'fields': ('cliente', 'cliente_identificacion', 'cliente_direccion', 'cliente_es_residente')
        }),
        ('Fechas', {
            'fields': ('fecha_emision', 'fecha_vencimiento')
        }),
        ('Emisor', {
            'fields': ('emisor_rif', 'emisor_razon_social', 'emisor_direccion_fiscal', 
                      'es_sujeto_pasivo_especial', 'esta_inscrita_rtn')
        }),
        ('Operación', {
            'fields': ('tipo_operacion', 'moneda', 'moneda_operacion', 'tasa_cambio_bcv')
        }),
        ('Bases Imponibles (USD)', {
            'fields': ('subtotal_base_gravada', 'subtotal_exento', 'subtotal_exportacion')
        }),
        ('Impuestos (USD)', {
            'fields': ('monto_iva_16', 'monto_iva_adicional', 'monto_igtf')
        }),
        ('Totales (USD)', {
            'fields': ('subtotal', 'monto_total', 'saldo_pendiente')
        }),
        ('Equivalentes en Bolívares', {
            'fields': ('subtotal_base_gravada_bs', 'subtotal_exento_bs', 'monto_iva_16_bs', 
                      'monto_igtf_bs', 'monto_total_bs'),
            'classes': ('collapse',)
        }),
        ('Intermediación', {
            'fields': ('tercero_rif', 'tercero_razon_social'),
            'classes': ('collapse',)
        }),
        ('Digital', {
            'fields': ('modalidad_emision', 'firma_digital')
        }),
        ('Estado y Archivos', {
            'fields': ('estado', 'archivo_pdf', 'asiento_contable_factura', 'notas')
        }),
    )


@admin.register(ItemFacturaConsolidada)
class ItemFacturaConsolidadaAdmin(admin.ModelAdmin):
    list_display = ('factura', 'descripcion', 'cantidad', 'precio_unitario', 'subtotal_item', 
                   'tipo_servicio', 'es_gravado')
    list_filter = ('tipo_servicio', 'es_gravado')
    search_fields = ('descripcion', 'factura__numero_factura', 'nombre_pasajero', 'numero_boleto')
    readonly_fields = ('subtotal_item',)


@admin.register(DocumentoExportacionConsolidado)
class DocumentoExportacionConsolidadoAdmin(admin.ModelAdmin):
    list_display = ('factura', 'tipo_documento', 'numero_documento', 'fecha_subida')
    list_filter = ('tipo_documento', 'fecha_subida')
    search_fields = ('numero_documento', 'factura__numero_factura')

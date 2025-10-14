# Archivo: core/admin_venezuela.py
"""
Admin interface para modelos de facturación venezolana.
Proporciona interface administrativa específica para cumplimiento fiscal.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models.facturacion_venezuela import (
    FacturaVenezuela, 
    ItemFacturaVenezuela, 
    DocumentoExportacion,
    NotaDebitoVenezuela
)


class ItemFacturaVenezuelaInline(admin.TabularInline):
    """Inline para items de factura venezolana"""
    model = ItemFacturaVenezuela
    extra = 1
    fields = [
        'descripcion', 'cantidad', 'precio_unitario', 'subtotal_item',
        'tipo_servicio', 'es_gravado', 'alicuota_iva',
        'nombre_pasajero', 'numero_boleto', 'itinerario', 'codigo_aerolinea'
    ]
    readonly_fields = ['subtotal_item']


class DocumentoExportacionInline(admin.TabularInline):
    """Inline para documentos de exportación"""
    model = DocumentoExportacion
    extra = 0
    fields = ['tipo_documento', 'numero_documento', 'archivo', 'fecha_subida']
    readonly_fields = ['fecha_subida']


@admin.register(FacturaVenezuela)
class FacturaVenezuelaAdmin(admin.ModelAdmin):
    """Admin para facturas venezolanas con campos fiscales específicos"""
    
    list_display = [
        'numero_factura', 'cliente', 'fecha_emision', 'tipo_operacion',
        'moneda_operacion', 'monto_total', 'estado', 'es_sujeto_pasivo_especial'
    ]
    
    list_filter = [
        'estado', 'tipo_operacion', 'moneda_operacion', 'modalidad_emision',
        'es_sujeto_pasivo_especial', 'cliente_es_residente', 'fecha_emision'
    ]
    
    search_fields = [
        'numero_factura', 'numero_control', 'cliente__nombre',
        'emisor_rif', 'tercero_rif'
    ]
    
    readonly_fields = [
        'monto_total', 'saldo_pendiente', 'subtotal_base_gravada',
        'subtotal_exento', 'subtotal_exportacion', 'monto_iva_16',
        'monto_iva_adicional', 'monto_igtf', 'subtotal_base_gravada_bs',
        'subtotal_exento_bs', 'monto_iva_16_bs', 'monto_igtf_bs', 'monto_total_bs'
    ]
    
    fieldsets = [
        (_('Información Básica'), {
            'fields': [
                'numero_factura', 'numero_control', 'fecha_emision', 'fecha_vencimiento',
                'modalidad_emision', 'firma_digital'
            ]
        }),
        (_('Emisor (Agencia)'), {
            'fields': [
                'emisor_rif', 'emisor_razon_social', 'emisor_direccion_fiscal',
                'es_sujeto_pasivo_especial', 'esta_inscrita_rtn'
            ]
        }),
        (_('Cliente'), {
            'fields': [
                'cliente', 'cliente_es_residente', 'cliente_identificacion',
                'cliente_direccion'
            ]
        }),
        (_('Operación'), {
            'fields': [
                'tipo_operacion', 'moneda_operacion', 'moneda', 'tasa_cambio_bcv',
                'venta_asociada'
            ]
        }),
        (_('Tercero (Intermediación)'), {
            'fields': ['tercero_rif', 'tercero_razon_social'],
            'classes': ['collapse']
        }),
        (_('Bases Imponibles'), {
            'fields': [
                'subtotal_base_gravada', 'subtotal_exento', 'subtotal_exportacion'
            ],
            'classes': ['collapse']
        }),
        (_('Impuestos Calculados'), {
            'fields': [
                'monto_iva_16', 'monto_iva_adicional', 'monto_igtf'
            ],
            'classes': ['collapse']
        }),
        (_('Equivalencias en Bolívares'), {
            'fields': [
                'subtotal_base_gravada_bs', 'subtotal_exento_bs',
                'monto_iva_16_bs', 'monto_igtf_bs', 'monto_total_bs'
            ],
            'classes': ['collapse']
        }),
        (_('Totales'), {
            'fields': [
                'subtotal', 'monto_impuestos', 'monto_total', 'saldo_pendiente', 'estado'
            ]
        }),
        (_('Otros'), {
            'fields': ['notas', 'archivo_pdf'],
            'classes': ['collapse']
        })
    ]
    
    inlines = [ItemFacturaVenezuelaInline, DocumentoExportacionInline]
    
    actions = ['calcular_impuestos', 'generar_pdf_venezuela']
    
    def calcular_impuestos(self, request, queryset):
        """Acción para recalcular impuestos de facturas seleccionadas"""
        count = 0
        for factura in queryset:
            try:
                factura.calcular_impuestos_venezuela()
                factura.save()
                count += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f"Error calculando impuestos para {factura.numero_factura}: {e}",
                    level='ERROR'
                )
        
        if count > 0:
            self.message_user(
                request,
                f"Impuestos recalculados para {count} facturas.",
                level='SUCCESS'
            )
    
    calcular_impuestos.short_description = _("Recalcular impuestos venezolanos")
    
    def generar_pdf_venezuela(self, request, queryset):
        """Acción para generar PDFs con formato venezolano"""
        # TODO: Implementar generación de PDF específico para Venezuela
        self.message_user(
            request,
            "Generación de PDF venezolano pendiente de implementación.",
            level='INFO'
        )
    
    generar_pdf_venezuela.short_description = _("Generar PDF formato Venezuela")
    
    def get_readonly_fields(self, request, obj=None):
        """Campos de solo lectura dinámicos"""
        readonly = list(self.readonly_fields)
        
        # Si la factura ya está emitida, algunos campos no se pueden cambiar
        if obj and obj.estado != FacturaVenezuela.EstadoFactura.BORRADOR:
            readonly.extend([
                'tipo_operacion', 'moneda_operacion', 'cliente_es_residente',
                'es_sujeto_pasivo_especial'
            ])
        
        return readonly
    
    def save_model(self, request, obj, form, change):
        """Guarda el modelo y recalcula impuestos"""
        super().save_model(request, obj, form, change)
        
        # Recalcular impuestos después de guardar
        if obj.pk and obj.items_factura.exists():
            try:
                obj.calcular_impuestos_venezuela()
                obj.save()
            except Exception as e:
                self.message_user(
                    request,
                    f"Error calculando impuestos: {e}",
                    level='ERROR'
                )


@admin.register(ItemFacturaVenezuela)
class ItemFacturaVenezuelaAdmin(admin.ModelAdmin):
    """Admin para items de factura venezolana"""
    
    list_display = [
        'factura', 'descripcion', 'cantidad', 'precio_unitario',
        'subtotal_item', 'tipo_servicio', 'es_gravado'
    ]
    
    list_filter = ['tipo_servicio', 'es_gravado', 'alicuota_iva']
    
    search_fields = [
        'descripcion', 'nombre_pasajero', 'numero_boleto',
        'factura__numero_factura'
    ]
    
    fieldsets = [
        (_('Información Básica'), {
            'fields': [
                'factura', 'descripcion', 'cantidad', 'precio_unitario', 'subtotal_item'
            ]
        }),
        (_('Clasificación Fiscal'), {
            'fields': ['tipo_servicio', 'es_gravado', 'alicuota_iva']
        }),
        (_('Datos Boleto Aéreo'), {
            'fields': [
                'nombre_pasajero', 'numero_boleto', 'itinerario', 'codigo_aerolinea'
            ],
            'classes': ['collapse']
        })
    ]
    
    readonly_fields = ['subtotal_item']


@admin.register(DocumentoExportacion)
class DocumentoExportacionAdmin(admin.ModelAdmin):
    """Admin para documentos de exportación"""
    
    list_display = [
        'factura', 'tipo_documento', 'numero_documento', 'fecha_subida'
    ]
    
    list_filter = ['tipo_documento', 'fecha_subida']
    
    search_fields = [
        'numero_documento', 'factura__numero_factura'
    ]
    
    readonly_fields = ['fecha_subida']
    
    def get_queryset(self, request):
        """Optimiza consultas"""
        return super().get_queryset(request).select_related('factura')


@admin.register(NotaDebitoVenezuela)
class NotaDebitoVenezuelaAdmin(admin.ModelAdmin):
    """Admin para Notas de Débito por diferencial cambiario"""
    
    list_display = [
        'numero_nota_debito', 'factura_origen', 'fecha_emision',
        'ganancia_cambiaria_bsd', 'monto_iva_bsd', 'estado'
    ]
    
    list_filter = ['estado', 'fecha_emision']
    
    search_fields = [
        'numero_nota_debito', 'factura_origen__numero_factura',
        'referencia_pago'
    ]
    
    readonly_fields = [
        'numero_nota_debito', 'creado', 'actualizado'
    ]
    
    fieldsets = [
        (_('Información Básica'), {
            'fields': [
                'numero_nota_debito', 'factura_origen', 'fecha_emision', 'estado'
            ]
        }),
        (_('Diferencial Cambiario'), {
            'fields': [
                'ganancia_cambiaria_bsd', 'monto_iva_bsd',
                'tasa_factura', 'tasa_pago'
            ]
        }),
        (_('Referencia'), {
            'fields': ['referencia_pago', 'observaciones']
        }),
        (_('Auditoría'), {
            'fields': ['creado', 'actualizado'],
            'classes': ['collapse']
        })
    ]
    
    def has_add_permission(self, request):
        """No permitir creación manual - solo automática"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Solo superusuarios pueden eliminar"""
        return request.user.is_superuser
    
    def get_queryset(self, request):
        """Optimiza consultas"""
        return super().get_queryset(request).select_related('factura_origen')
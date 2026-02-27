from django.contrib import admin
from core.admin_saas import SaaSAdminMixin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Factura, ItemFactura, ReporteProveedor, ItemReporte, 
    DiferenciaFinanciera, GastoOperativo, PagoBinance
)

class ItemFacturaInline(admin.TabularInline):
    model = ItemFactura
    extra = 1

@admin.register(Factura)
class FacturaAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ('numero_factura', 'cliente', 'fecha_emision', 'estado', 'monto_total', 'saldo_pendiente')
    list_filter = ('estado', 'tipo_factura', 'fecha_emision')
    search_fields = ('numero_factura', 'cliente__nombre_completo', 'numero_control')
    inlines = [ItemFacturaInline]
    
    actions = ['generar_pdf_selectos']

    def generar_pdf_selectos(self, request, queryset):
        # Lógica para disparar la generación masiva de PDFs si fuera necesario
        pass
    generar_pdf_selectos.short_description = "Generar PDFs para facturas seleccionadas"

class ItemReporteInline(admin.TabularInline):
    model = ItemReporte
    extra = 0
    readonly_fields = ('numero_boleto', 'monto_total_proveedor', 'tax_proveedor', 'comision_proveedor', 'boleto_interno', 'estado')
    can_delete = False

@admin.register(ReporteProveedor)
class ReporteProveedorAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'proveedor', 'fecha_carga', 'estado', 'total_registros', 'total_con_diferencia', 'procesar_btn')
    list_filter = ('estado', 'proveedor')
    inlines = [ItemReporteInline]

    def procesar_btn(self, obj):
        if obj.estado == ReporteProveedor.EstadoReporte.PENDIENTE:
            return format_html(
                '<a class="button" href="{}">🚀 Procesar con IA</a>',
                reverse('admin:finance_reporteproveedor_process', args=[obj.pk])
            )
        return obj.get_estado_display()
    procesar_btn.short_description = "Acción"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:report_id>/process/', self.admin_site.admin_view(self.process_view), name='finance_reporteproveedor_process'),
        ]
        return custom_urls + urls

    def process_view(self, request, report_id):
        from django.contrib import messages
        from django.shortcuts import redirect
        from .services.reconciliation_service import ReconciliationService
        
        try:
            ReconciliationService.process_report(report_id)
            messages.success(request, f"Reporte {report_id} procesado exitosamente.")
        except Exception as e:
            messages.error(request, f"Error procesando reporte: {e}")
        
        return redirect('admin:finance_reporteproveedor_changelist')

@admin.register(ItemReporte)
class ItemReporteAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = 'reporte__agencia'
    list_display = ('numero_boleto', 'reporte', 'monto_total_proveedor', 'estado', 'boleto_interno')
    list_filter = ('estado', 'reporte__proveedor')
    search_fields = ('numero_boleto',)

@admin.register(DiferenciaFinanciera)
class DiferenciaFinancieraAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = 'item_reporte__reporte__agencia'
    list_display = ('item_reporte', 'campo_discrepancia', 'valor_sistema', 'valor_proveedor', 'diferencia', 'resuelto')
    list_filter = ('resuelto', 'campo_discrepancia')
    search_fields = ('item_reporte__numero_boleto',)

@admin.register(GastoOperativo)
class GastoOperativoAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ('fecha', 'descripcion', 'moneda', 'monto', 'categoria', 'creado_por')
    list_filter = ('fecha', 'categoria', 'moneda')
    search_fields = ('descripcion', 'categoria')
    date_hierarchy = 'fecha'

@admin.register(PagoBinance)
class PagoBinanceAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = 'factura__agencia'
    list_display = ('merchant_trade_no', 'factura', 'monto', 'moneda', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'moneda', 'fecha_creacion')
    search_fields = ('merchant_trade_no', 'factura__numero_factura', 'prepay_id')
    readonly_fields = ('merchant_trade_no', 'prepay_id', 'checkout_url', 'raw_response')

from django.contrib import admin
from django.core.files.base import ContentFile
from django.utils.html import format_html
from .models import Cotizacion, ItemCotizacion
from .pdf_service import generar_pdf_cotizacion

class ItemCotizacionInline(admin.TabularInline):
    model = ItemCotizacion
    extra = 1
    fields = ('tipo_item', 'descripcion', 'costo')
    readonly_fields = ()

@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ('numero_cotizacion', 'cliente_display', 'destino', 'fecha_emision', 'total_cotizado', 'consultor', 'estado')
    search_fields = ('numero_cotizacion', 'uuid', 'cliente__nombres', 'cliente__apellidos', 'nombre_cliente_manual', 'destino')
    list_filter = ('estado', 'fecha_emision', 'consultor')
    autocomplete_fields = ['cliente', 'consultor']
    inlines = [ItemCotizacionInline]
    readonly_fields = ('numero_cotizacion', 'uuid', 'total_cotizado', 'ver_pdf', 'ver_link_publico')
    actions = ['generar_pdf_action']

    fieldsets = (
        (None, {
            'fields': ('numero_cotizacion', 'uuid', 'estado', 'consultor')
        }),
        ('Magic IA (Cotizador)', {
            'fields': ('gds_raw_text', 'agency_fee', 'image_url', 'metadata_ia', 'ver_link_publico'),
            'classes': ('collapse',),
        }),
        ('Cliente', {
            'fields': ('cliente', 'nombre_cliente_manual'),
            'description': 'Seleccione un cliente registrado o ingrese un nombre para un prospecto.'
        }),
        ('Detalles del Viaje', {
            'fields': ('destino', 'fecha_emision', 'fecha_validez')
        }),
        ('Financiero', {
            'fields': ('total_cotizado',)
        }),
        ('Términos y PDF', {
            'fields': ('condiciones_comerciales', 'notas_internas', 'ver_pdf')
        }),
    )

    def cliente_display(self, obj):
        return obj.cliente if obj.cliente else f"{obj.nombre_cliente_manual} (Manual)"
    cliente_display.short_description = "Cliente"

    def ver_pdf(self, obj):
        if obj.archivo_pdf:
            return format_html('<a href="{}" target="_blank">📄 Ver PDF Generado</a>', obj.archivo_pdf.url)
        return "Sin PDF."
    ver_pdf.short_description = "Archivo PDF"

    def ver_link_publico(self, obj):
        if obj.uuid:
            from django.urls import reverse
            url = reverse('cotizaciones:public_quote', kwargs={'quote_uuid': obj.uuid})
            return format_html('<a href="{}" target="_blank">🔗 Link Público para WhatsApp</a>', url)
        return "-"
    ver_link_publico.short_description = "Link Público"

    @admin.action(description='Generar PDF de Cotización')
    def generar_pdf_action(self, request, queryset):
        for cotizacion in queryset:
            try:
                # Asegurar cálculo antes de generar
                cotizacion.calcular_total()
                pdf_bytes = generar_pdf_cotizacion(cotizacion)
                pdf_filename = f"cotizacion_{cotizacion.numero_cotizacion}.pdf"
                cotizacion.archivo_pdf.save(pdf_filename, ContentFile(pdf_bytes), save=True)
                self.message_user(request, f"PDF generado para la cotización {cotizacion.numero_cotizacion}")
            except Exception as e:
                self.message_user(request, f"Error al generar PDF para {cotizacion.numero_cotizacion}: {e}", level='error')

    def save_model(self, request, obj, form, change):
        if not obj.consultor_id:
            obj.consultor = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.calcular_total()

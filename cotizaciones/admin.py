from django.contrib import admin
from django.core.files.base import ContentFile
from django.utils.html import format_html
from .models import Cotizacion, ItemCotizacion
from .pdf_service import generar_pdf_cotizacion

class ItemCotizacionInline(admin.TabularInline):
    model = ItemCotizacion
    extra = 1
    # We can add a custom form later to pretty-print the JSONField
    fields = ('tipo_item', 'descripcion', 'costo', 'detalles_json')
    readonly_fields = ()

@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ('numero_cotizacion', 'cliente', 'destino', 'fecha_emision', 'total_cotizado', 'consultor', 'estado')
    search_fields = ('numero_cotizacion', 'cliente__nombres', 'cliente__apellidos', 'destino')
    list_filter = ('estado', 'fecha_emision', 'consultor')
    autocomplete_fields = ['cliente', 'consultor']
    inlines = [ItemCotizacionInline]
    readonly_fields = ('numero_cotizacion', 'total_cotizado', 'ver_pdf')
    actions = ['generar_pdf_action']

    fieldsets = (
        (None, {
            'fields': ('numero_cotizacion', 'estado', 'cliente', 'consultor')
        }),
        ('Detalles del Viaje', {
            'fields': ('destino', 'numero_pasajeros', 'fecha_emision', 'fecha_vencimiento')
        }),
        ('Financiero', {
            'fields': ('total_cotizado',)
        }),
        ('Términos y PDF', {
            'fields': ('terminos_pago', 'terminos_cancelacion', 'notas', 'ver_pdf')
        }),
    )

    def ver_pdf(self, obj):
        if obj.archivo_pdf:
            return format_html('<a href="{}" target="_blank">Ver PDF Generado</a>', obj.archivo_pdf.url)
        return "Aún no se ha generado el PDF."
    ver_pdf.short_description = "Archivo PDF"

    @admin.action(description='Generar PDF de Cotización')
    def generar_pdf_action(self, request, queryset):
        for cotizacion in queryset:
            try:
                pdf_bytes = generar_pdf_cotizacion(cotizacion)
                pdf_filename = f"cotizacion_{cotizacion.numero_cotizacion}.pdf"
                cotizacion.archivo_pdf.save(pdf_filename, ContentFile(pdf_bytes), save=True)
                self.message_user(request, f"PDF generado para la cotización {cotizacion.numero_cotizacion}")
            except Exception as e:
                self.message_user(request, f"Error al generar PDF para {cotizacion.numero_cotizacion}: {e}", level='error')

    def save_model(self, request, obj, form, change):
        # Asignar el usuario actual como consultor si no está ya asignado
        if not obj.consultor_id:
            obj.consultor = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Recalcular el total después de guardar los items
        form.instance.calcular_total()

import logging
from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.core.files.base import ContentFile
from django.contrib import messages

from core.services.pdf_service import generar_pdf_factura, generar_pdf_voucher_unificado
from core.admin_migration import MigrationCheckInline, validate_migration_requirements_action
from core.admin_saas import SaaSAdminMixin
from core.models_catalogos import Moneda, ProductoServicio, Proveedor
from apps.crm.models import Cliente
from .models import (
    Venta, BoletoImportado, ItemVenta, SegmentoVuelo, 
    AlojamientoReserva, TrasladoServicio, ActividadServicio,
    AlquilerAutoReserva, ServicioAdicionalDetalle, 
    FeeVenta, PagoVenta, AuditLog, VentaParseMetadata,
    CircuitoTuristico, CircuitoDia, PaqueteAereo, EventoServicio
)

logger = logging.getLogger(__name__)

# --- Formulario para la acción de facturación ---
class ClienteSelectionForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(),
        label="Seleccionar Cliente para facturar",
        required=True
    )

# --- Inlines ---

class ItemVentaInline(admin.TabularInline):
    model = ItemVenta
    extra = 1
    autocomplete_fields = ['producto_servicio', 'proveedor_servicio']
    readonly_fields = ('subtotal_item_venta', 'total_item_venta')
    fields = ('producto_servicio', 'descripcion_personalizada', 'cantidad', 'precio_unitario_venta', 'impuestos_item_venta', 'costo_neto_proveedor', 'fee_proveedor', 'comision_agencia_monto', 'fee_agencia_interno', 'subtotal_item_venta', 'total_item_venta')

class SegmentoVueloInline(admin.TabularInline):
    model = SegmentoVuelo
    extra = 0
    autocomplete_fields = ['origen', 'destino']

class AlojamientoReservaInline(admin.TabularInline):
    model = AlojamientoReserva
    extra = 0
    autocomplete_fields = ['proveedor', 'ciudad']

class AlquilerAutoReservaInline(admin.StackedInline):
    model = AlquilerAutoReserva
    extra = 0
    autocomplete_fields = ['proveedor', 'ciudad_retiro', 'ciudad_devolucion']
    fieldsets = (
        ('Información del Vehículo', {
            'fields': (('compania_rentadora', 'categoria_auto'), ('numero_confirmacion', 'nombre_conductor'))
        }),
        ('Itinerario', {
            'fields': (('fecha_hora_retiro', 'ciudad_retiro'), ('fecha_hora_devolucion', 'ciudad_devolucion'))
        }),
        ('Costos y Proveedor', {
            'fields': (('costo_neto', 'precio_venta'), ('incluye_seguro', 'proveedor'))
        }),
        ('Notas', {
            'fields': ('notas',),
            'classes': ('collapse',)
        }),
    )

class ServicioAdicionalDetalleInline(admin.StackedInline):
    model = ServicioAdicionalDetalle
    extra = 0
    autocomplete_fields = ['proveedor']
    fieldsets = (
        ('Información Básica', {
            'fields': (('tipo_servicio', 'descripcion'), ('codigo_referencia', 'proveedor'))
        }),
        ('Fechas y Pasajero', {
            'fields': (('fecha_inicio', 'fecha_fin'), ('nombre_pasajero', 'pasaporte_pasajero'))
        }),
        ('Costos y Precios', {
            'fields': (('costo_neto', 'precio_venta'),)
        }),
        ('Detalles del Servicio', {
            'fields': ('detalles_cobertura', 'contacto_emergencia', 'participantes', 'operado_por', 'hora_lugar_encuentro', 'duracion_estimada', 'inclusiones_servicio', 'recomendaciones'),
            'classes': ('collapse',)
        }),
    )

class TrasladoServicioInline(admin.TabularInline):
    model = TrasladoServicio
    extra = 0
    autocomplete_fields = ['proveedor']

class ActividadServicioInline(admin.TabularInline):
    model = ActividadServicio
    extra = 0
    autocomplete_fields = ['proveedor']

class FeeVentaInline(admin.TabularInline):
    model = FeeVenta
    extra = 0
    autocomplete_fields = ['moneda']

class PagoVentaInline(admin.TabularInline):
    model = PagoVenta
    extra = 0
    autocomplete_fields = ['moneda']

class CircuitoDiaInline(admin.TabularInline):
    model = CircuitoDia
    extra = 0
    autocomplete_fields = ['ciudad']

# --- Admins ---

class VentaAdminForm(forms.ModelForm):
    boleto_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    class Meta:
        model = Venta
        fields = '__all__'

@admin.register(Venta)
class VentaAdmin(SaaSAdminMixin, admin.ModelAdmin):
    form = VentaAdminForm
    list_display = ('venta_link', 'cliente', 'fecha_venta', 'total_venta', 'estado', 'tipo_venta', 'canal_origen', 'saldo_pendiente')
    list_display_links = ('venta_link',)
    search_fields = ('localizador', 'id_venta', 'cliente__nombres', 'cliente__apellidos')
    list_filter = ('estado', 'fecha_venta', 'tipo_venta', 'canal_origen')
    autocomplete_fields = ['cliente', 'moneda', 'cotizacion_origen', 'asiento_contable_venta']
    inlines = [
        ItemVentaInline, SegmentoVueloInline, AlojamientoReservaInline, 
        AlquilerAutoReservaInline, ServicioAdicionalDetalleInline, 
        TrasladoServicioInline, ActividadServicioInline, 
        FeeVentaInline, PagoVentaInline, MigrationCheckInline
    ]
    readonly_fields = ('total_venta', 'saldo_pendiente', 'boleto_importado_link', 'margen_estimado')
    actions = ['generar_links_de_pago', 'asignar_cliente_y_facturar', 'generar_liquidaciones_proveedor', 'generar_voucher_unificado', 'generar_doble_facturacion', 'hard_delete_ventas', validate_migration_requirements_action]

    @admin.action(description="🔥 ELIMINACIÓN FÍSICA (Irreversible)")
    def hard_delete_ventas(self, request, queryset):
        count = queryset.count()
        # Usamos delete() sobre el queryset de all_objects si es safedelete, 
        # o simplemente delete() si ya es el manager por defecto
        if hasattr(queryset, 'all_objects'):
            queryset.all_objects().delete()
        else:
            queryset.delete()
        self.message_user(request, f"Se han eliminado físicamente {count} ventas.")

    def has_add_permission(self, request):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    @admin.action(description="✨ Generar Link de Pago B2C para Ventas seleccionadas")
    def generar_links_de_pago(self, request, queryset):
        from apps.finance.models import LinkDePago
        creados = 0
        existentes = 0
        for venta in queryset:
            if not hasattr(venta, 'link_pago'):
                LinkDePago.objects.create(
                    venta=venta,
                    monto_total=venta.total_venta,
                    moneda=venta.moneda.codigo_iso if (venta.moneda and hasattr(venta.moneda, 'codigo_iso')) else 'USD'
                )
                creados += 1
            else:
                existentes += 1
        
        mensaje = f"Se generaron {creados} links de pago nuevos. {existentes} ventas ya tenían link."
        self.message_user(request, mensaje)

    def generar_doble_facturacion(self, request, queryset):
        from apps.finance.services.invoice_service import InvoiceService
        procesados = 0
        for venta in queryset:
            try:
                InvoiceService.generate_double_invoice(venta)
                procesados += 1
            except Exception as e:
                self.message_user(request, f"Error en Venta {venta.pk}: {str(e)}", level='error')
        
        if procesados:
            self.message_user(request, f"Doble facturación generada para {procesados} venta(s).")
    generar_doble_facturacion.short_description = "Generar Doble Facturación (Intermediación + Propia)"

    def venta_link(self, obj):
        url = reverse('admin:bookings_venta_change', args=[obj.id_venta])
        display_text = obj.localizador or f"Venta #{obj.id_venta}"
        return format_html('<a href="{}">{}</a>', url, display_text)
    venta_link.short_description = "Venta (ID/Localizador)"

    def generar_voucher_unificado(self, request, queryset):
        if queryset.count() != 1:
            messages.error(request, "Por favor, seleccione exactamente una Venta para generar el voucher unificado.")
            return

        venta = queryset.first()
        pdf_bytes, filename = generar_pdf_voucher_unificado(venta.pk)

        if pdf_bytes:
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            messages.error(request, f"No se pudo generar el voucher para la Venta {venta.localizador or venta.id_venta}.")

    generar_voucher_unificado.short_description = "Generar Voucher Unificado (PDF)"

    def asignar_cliente_y_facturar(self, request, queryset):
        queryset = queryset.filter(cliente__isnull=True, factura__isnull=True)
        if not queryset.exists():
            self.message_user(request, "Las ventas seleccionadas ya tienen un cliente o ya han sido facturadas.", level='warning')
            return

        form = ClienteSelectionForm(request.POST or None)
        if 'apply' in request.POST and form.is_valid():
            cliente = form.cleaned_data['cliente']
            from core.services.facturacion_service import FacturacionService
            facturas_creadas = 0
            for venta in queryset:
                try:
                    venta.cliente = cliente
                    venta.save(update_fields=['cliente'])
                    factura = FacturacionService.generar_factura_desde_venta(venta, cliente)
                    pdf_bytes, pdf_filename = generar_pdf_factura(factura.pk)
                    if pdf_bytes:
                        factura.archivo_pdf.save(pdf_filename, ContentFile(pdf_bytes), save=True)
                    facturas_creadas += 1
                except Exception as e:
                    self.message_user(request, f"Error en Venta {venta.id_venta}: {str(e)}", level='error')

            if facturas_creadas:
                self.message_user(request, f"{facturas_creadas} factura(s) generada(s) exitosamente.")
            return HttpResponseRedirect(request.get_full_path())

        context = {'ventas': queryset, 'cliente_form': form, 'title': 'Asignar Cliente y Facturar', 'opts': self.model._meta}
        return render(request, 'admin/asignar_cliente_y_facturar.html', context)

    @admin.action(description="Generar Liquidación a Proveedor(es)")
    def generar_liquidaciones_proveedor(self, request, queryset):
        from collections import defaultdict
        from core.models.contabilidad import LiquidacionProveedor, ItemLiquidacion
        liquidaciones_creadas = 0
        for venta in queryset:
            items_por_proveedor = defaultdict(list)
            for item in venta.items_venta.all():
                if item.proveedor_servicio and item.costo_neto_proveedor is not None:
                    items_por_proveedor[item.proveedor_servicio].append(item)

            for proveedor, items in items_por_proveedor.items():
                if not LiquidacionProveedor.objects.filter(proveedor=proveedor, venta=venta).exists():
                    monto_total = sum((i.costo_neto_proveedor or 0) + (i.fee_proveedor or 0) - (i.comision_agencia_monto or 0) for i in items)
                    if monto_total > 0:
                        liquidacion = LiquidacionProveedor.objects.create(proveedor=proveedor, venta=venta, monto_total=monto_total)
                        for i in items:
                            ItemLiquidacion.objects.create(liquidacion=liquidacion, item_venta=i, descripcion=i.descripcion_personalizada, monto=(i.costo_neto_proveedor or 0) + (i.fee_proveedor or 0) - (i.comision_agencia_monto or 0))
                        liquidaciones_creadas += 1
        self.message_user(request, f"Se generaron {liquidaciones_creadas} liquidaciones.")

    def boleto_importado_link(self, obj):
        boleto = BoletoImportado.objects.filter(venta_asociada=obj).first()
        if boleto:
            url = reverse('admin:bookings_boletoimportado_change', args=[boleto.pk])
            return format_html('<a href="{}">Ver Boleto Original (ID: {})</a>', url, boleto.pk)
        return "N/A"
    boleto_importado_link.short_description = "Boleto de Origen"

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        boleto_id = request.GET.get('boleto_id')
        if boleto_id:
            try:
                boleto = BoletoImportado.objects.get(pk=boleto_id)
                initial.update({'subtotal': boleto.tarifa_base, 'impuestos': boleto.impuestos_total_calculado, 'localizador': boleto.localizador_pnr})
            except BoletoImportado.DoesNotExist: pass
        return initial

@admin.register(BoletoImportado)
class BoletoImportadoAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ('id_boleto_importado', 'archivo_boleto_link', 'pdf_generado_link', 'fecha_subida', 'estado_parseo', 'numero_boleto', 'nombre_pasajero_procesado', 'venta_asociada')
    search_fields = ('archivo_boleto', 'numero_boleto', 'nombre_pasajero_completo')
    list_filter = ('estado_parseo', 'formato_detectado', 'fecha_subida')
    readonly_fields = ('fecha_subida', 'formato_detectado', 'datos_parseados', 'estado_parseo', 'log_parseo', 'pdf_generado_link')
    autocomplete_fields = ['venta_asociada']
    actions = ['reprocesar_boletos', 'hard_delete_boletos']
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # Enlace al dashboard de subida
        extra_context['show_upload_button'] = True
        return super().changelist_view(request, extra_context=extra_context)

    @admin.action(description="🔥 ELIMINACIÓN FÍSICA (Irreversible)")
    def hard_delete_boletos(self, request, queryset):
        count = queryset.count()
        for obj in queryset:
            # Borrar archivo físico también
            if obj.archivo_boleto:
                try:
                    obj.archivo_boleto.delete(save=False)
                except Exception: pass
            if obj.archivo_pdf_generado:
                try:
                    obj.archivo_pdf_generado.delete(save=False)
                except Exception: pass
            
            # Forzar eliminación física (bypass soft delete)
            if hasattr(obj, 'delete') and 'force_policy' in str(obj.delete):
                obj.delete(force_policy=True)
            else:
                obj.delete()
        
        self.message_user(request, f"Se han eliminado físicamente {count} boletos y sus archivos.")

    def has_add_permission(self, request):
        return True # Asegurar que siempre pueda agregar boletos manualmente

    @admin.action(description="🔄 Reprocesar Boletos Seleccionados")
    def reprocesar_boletos(self, request, queryset):
        from core.services.ticket_parser_service import TicketParserService
        service = TicketParserService()
        exitos = 0
        errores = 0
        
        for boleto in queryset:
            try:
                # Forzar el reprocesamiento usando el archivo original
                service.procesar_boleto(boleto.pk)
                exitos += 1
            except Exception as e:
                logger.error(f"Error reprocesando boleto {boleto.pk}: {e}")
                errores += 1
        
        if exitos:
            self.message_user(request, f"Se reprocesaron {exitos} boletos exitosamente.")
        if errores:
            self.message_user(request, f"Falló el reprocesamiento de {errores} boletos. Revise los logs.", level='error')
    
    def archivo_boleto_link(self, obj):
        if obj.archivo_boleto:
            return format_html("<a href='{url}'>{name}</a>", url=obj.archivo_boleto.url, name=obj.archivo_boleto.name.split('/')[-1])
        return "-"

    def pdf_generado_link(self, obj):
        url = obj.get_pdf_url()
        if url: return format_html('<a href="{}" target="_blank" class="button">📄 Ver PDF</a>', url)
        return "No generado"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            try:
                # 🧠 Lógica de Regeneración de PDF ante cambios manuales en el Admin
                # Si el usuario editó campos en el Admin, queremos que el PDF los refleje.
                data = obj.datos_parseados.copy() if (obj.datos_parseados and isinstance(obj.datos_parseados, dict)) else {}
                
                # Inyectamos la instancia para que el generador sepa dónde guardar y use los datos del objeto
                data['_boleto_instance'] = obj
                
                # Sincronizamos campos clave del objeto al diccionario de datos para la plantilla
                data['nombre_pasajero'] = obj.nombre_pasajero_procesado
                data['passenger_name'] = obj.nombre_pasajero_procesado
                data['numero_boleto'] = obj.numero_boleto
                data['ticket_number'] = obj.numero_boleto
                data['pnr'] = obj.localizador_pnr
                data['codigo_reserva'] = obj.localizador_pnr
                data['fecha_emision'] = obj.fecha_emision_boleto
                data['aerolinea_emisora'] = obj.aerolinea_emisora
                data['foid'] = obj.foid_pasajero
                data['passenger_document'] = obj.foid_pasajero
                data['total_boleto'] = obj.total_boleto
                
                from core.ticket_parser import generate_ticket
                from django.contrib import messages
                
                # Llamamos al generador unificado (ahora devuelve (bytes, filename) y persiste internamente)
                pdf_bytes, filename = generate_ticket(data, agencia_obj=obj.agencia)
                
                if pdf_bytes:
                    messages.success(request, f"✨ PDF regenerado exitosamente para el boleto {obj.numero_boleto or obj.pk}.")
                else:
                    messages.warning(request, "Se guardaron los cambios, pero falló la regeneración del PDF (verifique Gotenberg).")

            except Exception as e:
                logger.error(f"Error regenerando PDF desde Admin para Boleto {obj.pk}: {e}", exc_info=True)
                from django.contrib import messages
                messages.warning(request, f"Se actualizaron los datos, pero falló la regeneración del PDF: {e}")

@admin.register(AuditLog)
class AuditLogAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = 'venta__agencia'
    list_display = ('id_audit_log','modelo','object_id','accion','venta','creado')
    list_filter = ('modelo','accion','creado')
    readonly_fields = ('modelo','object_id','accion','venta','descripcion','datos_previos','datos_nuevos','metadata_extra','creado')
    ordering = ('-creado',)

@admin.register(VentaParseMetadata)
class VentaParseMetadataAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = 'venta__agencia'
    list_display = ('id_metadata','venta','fuente','creado')
    readonly_fields = ('raw_normalized_json','segments_json','creado')

@admin.register(AlquilerAutoReserva)
class AlquilerAutoReservaAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = 'venta__agencia'
    list_display = ('id_alquiler_auto','venta','compania_rentadora','fecha_hora_retiro')
    autocomplete_fields = ['venta','proveedor','ciudad_retiro','ciudad_devolucion']

@admin.register(EventoServicio)
class EventoServicioAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = 'venta__agencia'
    list_display = ('id_evento_servicio','venta','nombre_evento','fecha_evento')
    autocomplete_fields = ['venta','proveedor']

@admin.register(CircuitoTuristico)
class CircuitoTuristicoAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = 'venta__agencia'
    list_display = ('id_circuito','venta','nombre_circuito','fecha_inicio')
    autocomplete_fields = ['venta']

@admin.register(PaqueteAereo)
class PaqueteAereoAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = 'venta__agencia'
    list_display = ('id_paquete_aereo','venta','nombre_paquete')
    autocomplete_fields = ['venta']

@admin.register(ServicioAdicionalDetalle)
class ServicioAdicionalDetalleAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = 'venta__agencia'
    list_display = ('id_servicio_adicional','venta','tipo_servicio','codigo_referencia')
    autocomplete_fields = ['venta','proveedor']

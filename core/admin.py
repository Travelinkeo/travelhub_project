# Archivo: core/admin.py
from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django import forms

from .models import (
    Pais, Ciudad, Moneda, TipoCambio,
    Cliente, Proveedor, ProductoServicio, Cotizacion, ItemCotizacion,
    PlanContable, AsientoContable, DetalleAsiento,
    Venta, ItemVenta, Factura, ItemFactura,
    BoletoImportado,
    SegmentoVuelo, AlojamientoReserva, TrasladoServicio, ActividadServicio, PagoVenta, FeeVenta,
    PaginaCMS, DestinoCMS, PaqueteTuristicoCMS, ArticuloBlog, Testimonio,
    MenuItemCMS, FormularioContactoCMS
)

# --- Clases Admin para Configuración / Compartidos ---

@admin.register(Pais)
class PaisAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo_iso_2', 'codigo_iso_3')
    search_fields = ('nombre', 'codigo_iso_2', 'codigo_iso_3')

@admin.register(Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'pais', 'region_estado')
    search_fields = ('nombre', 'region_estado', 'pais__nombre')
    list_filter = ('pais',)
    autocomplete_fields = ['pais']

@admin.register(Moneda)
class MonedaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo_iso', 'simbolo', 'es_moneda_local')
    search_fields = ('nombre', 'codigo_iso')
    list_filter = ('es_moneda_local',)

@admin.register(TipoCambio)
class TipoCambioAdmin(admin.ModelAdmin):
    list_display = ('moneda_origen', 'moneda_destino', 'fecha_efectiva', 'tasa_conversion')
    search_fields = ('moneda_origen__codigo_iso', 'moneda_destino__codigo_iso')
    list_filter = ('fecha_efectiva', 'moneda_origen', 'moneda_destino')
    autocomplete_fields = ['moneda_origen', 'moneda_destino']
    date_hierarchy = 'fecha_efectiva'

# --- Clases Admin para CRM ---

class ItemCotizacionInline(admin.TabularInline):
    model = ItemCotizacion
    extra = 1
    autocomplete_fields = ['producto_servicio']

@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ('numero_cotizacion', 'cliente', 'fecha_emision', 'total_cotizado', 'moneda', 'estado')
    search_fields = ('numero_cotizacion', 'cliente__nombres', 'cliente__apellidos')
    list_filter = ('estado', 'fecha_emision')
    autocomplete_fields = ['cliente', 'moneda']
    inlines = [ItemCotizacionInline]
    readonly_fields = ('total_cotizado',)

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('get_nombre_completo', 'email', 'telefono_principal', 'tipo_cliente')
    search_fields = ('nombres', 'apellidos', 'nombre_empresa', 'email')
    list_filter = ('tipo_cliente',)
    autocomplete_fields = ['ciudad', 'pais_emision_pasaporte', 'nacionalidad']

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_proveedor', 'nivel_proveedor', 'activo')
    search_fields = ('nombre',)
    list_filter = ('tipo_proveedor', 'nivel_proveedor', 'activo')

@admin.register(ProductoServicio)
class ProductoServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_producto', 'proveedor_principal', 'activo')
    search_fields = ('nombre', 'codigo_interno')
    list_filter = ('tipo_producto', 'activo')
    autocomplete_fields = ['proveedor_principal', 'moneda_referencial']

# --- Clases Admin para ERP ---

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

class ItemVentaInline(admin.TabularInline):
    model = ItemVenta
    extra = 1
    autocomplete_fields = ['producto_servicio', 'proveedor_servicio']
    readonly_fields = ('subtotal_item_venta', 'total_item_venta')
    fields = ('producto_servicio', 'descripcion_personalizada', 'cantidad', 'precio_unitario_venta', 'impuestos_item_venta', 'subtotal_item_venta', 'total_item_venta')

class SegmentoVueloInline(admin.TabularInline):
    model = SegmentoVuelo
    extra = 0
    autocomplete_fields = ['origen', 'destino']

class AlojamientoReservaInline(admin.TabularInline):
    model = AlojamientoReserva
    extra = 0
    autocomplete_fields = ['proveedor', 'ciudad']

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

class VentaAdminForm(forms.ModelForm):
    boleto_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    class Meta:
        model = Venta
        fields = '__all__'

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    form = VentaAdminForm
    list_display = ('localizador', 'cliente', 'fecha_venta', 'total_venta', 'estado', 'tipo_venta', 'canal_origen', 'saldo_pendiente')
    search_fields = ('localizador', 'cliente__nombres', 'cliente__apellidos')
    list_filter = ('estado', 'fecha_venta', 'tipo_venta', 'canal_origen')
    autocomplete_fields = ['cliente', 'moneda', 'cotizacion_origen', 'asiento_contable_venta']
    inlines = [ItemVentaInline, SegmentoVueloInline, AlojamientoReservaInline, TrasladoServicioInline, ActividadServicioInline, FeeVentaInline, PagoVentaInline]
    readonly_fields = ('total_venta', 'saldo_pendiente', 'boleto_importado_link', 'margen_estimado')

    def boleto_importado_link(self, obj):
        boleto = BoletoImportado.objects.filter(venta_asociada=obj).first()
        if boleto:
            url = reverse('admin:core_boletoimportado_change', args=[boleto.pk])
            return format_html('<a href="{}">Ver Boleto Original (ID: {})</a>', url, boleto.pk)
        return "N/A (Creada manualmente)"
    boleto_importado_link.short_description = "Boleto de Origen"

    def get_fieldsets(self, request, obj=None):
        base_fieldsets = list(super().get_fieldsets(request, obj)) if obj else [
            (None, {'fields': self.get_fields(request, obj)})
        ]
        if obj:
            # Asegurarse de que 'fields' existe en el diccionario antes de modificarlo
            if 'fields' in base_fieldsets[0][1]:
                fields = list(base_fieldsets[0][1].get('fields', []))
                if 'boleto_importado_link' not in fields:
                    fields.append('boleto_importado_link')
                base_fieldsets[0][1]['fields'] = tuple(fields)
        return base_fieldsets

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        boleto_id = request.GET.get('boleto_id')
        if boleto_id:
            try:
                boleto = BoletoImportado.objects.get(pk=boleto_id)
                cliente = None
                if boleto.nombre_pasajero_procesado:
                    nombre_partes = boleto.nombre_pasajero_procesado.split()
                    if len(nombre_partes) > 1:
                        cliente = Cliente.objects.filter(nombres__icontains=nombre_partes[0], apellidos__icontains=nombre_partes[-1]).first()
                
                if cliente: initial['cliente'] = cliente.pk
                
                moneda_usd, _ = Moneda.objects.get_or_create(codigo_iso='USD', defaults={'nombre': 'Dólar Estadounidense'})
                initial['moneda'] = moneda_usd.pk
                initial['subtotal'] = boleto.tarifa_base or 0
                initial['impuestos'] = boleto.impuestos_total_calculado or 0
                initial['descripcion_general'] = f"Venta desde Boleto Nro: {boleto.numero_boleto} para {boleto.nombre_pasajero_completo}"
                initial['boleto_id'] = boleto.pk
            except BoletoImportado.DoesNotExist:
                pass
        return initial

    def get_formsets_with_inlines(self, request, obj=None):
        formsets = super().get_formsets_with_inlines(request, obj)
        boleto_id = request.GET.get('boleto_id')
        
        if obj is None and boleto_id:
            try:
                boleto = BoletoImportado.objects.get(pk=boleto_id)
                producto_aereo, _ = ProductoServicio.objects.get_or_create(tipo_producto='AIR', defaults={'nombre': 'Boleto Aéreo Genérico'})

                for formset in formsets:
                    if formset.model == ItemVenta:
                        formset.initial = [{
                            'producto_servicio': producto_aereo.pk,
                            'cantidad': 1,
                            'precio_unitario_venta': boleto.total_boleto or 0,
                            'descripcion_personalizada': f"Boleto: {boleto.numero_boleto}, Ruta: {boleto.ruta_vuelo.replace(chr(10), ' ') if boleto.ruta_vuelo else ''}",
                            'codigo_reserva_proveedor': boleto.localizador_pnr,
                        }]
                        formset.extra = 0
            except BoletoImportado.DoesNotExist:
                pass
        return formsets

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        boleto_id = form.cleaned_data.get('boleto_id')
        if boleto_id and not change:
            try:
                boleto = BoletoImportado.objects.get(pk=boleto_id)
                if not boleto.venta_asociada:
                    boleto.venta_asociada = obj
                    boleto.save(update_fields=['venta_asociada'])
            except BoletoImportado.DoesNotExist:
                pass

@admin.register(BoletoImportado)
class BoletoImportadoAdmin(admin.ModelAdmin):
    list_display = ('id_boleto_importado', 'archivo_boleto_link', 'fecha_subida', 'estado_parseo', 'numero_boleto', 'nombre_pasajero_procesado', 'venta_asociada')
    search_fields = ('archivo_boleto', 'numero_boleto', 'nombre_pasajero_completo')
    list_filter = ('estado_parseo', 'formato_detectado', 'fecha_subida')
    readonly_fields = (
        'fecha_subida', 'formato_detectado', 'datos_parseados', 'estado_parseo', 'log_parseo', 
        'numero_boleto', 'nombre_pasajero_completo', 'nombre_pasajero_procesado', 
        'ruta_vuelo', 'fecha_emision_boleto', 'aerolinea_emisora', 'direccion_aerolinea',
        'agente_emisor', 'foid_pasajero', 'localizador_pnr', 'tarifa_base', 
        'impuestos_descripcion', 'impuestos_total_calculado', 'total_boleto', 'crear_venta_desde_boleto_link'
    )
    actions = ['reintentar_parseo']
    autocomplete_fields = ['venta_asociada']
    
    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (None, {'fields': ('archivo_boleto', 'venta_asociada')}),
            (_("Información de Parseo (Automático)"), {'fields': ('estado_parseo', 'log_parseo', 'datos_parseados')}),
            (_("Datos Extraídos"), {'fields': ('numero_boleto', 'nombre_pasajero_procesado', 'total_boleto', 'localizador_pnr')}),
        ]
        if obj and (obj.estado_parseo == 'COM' or obj.venta_asociada):
            fieldsets.append((_("Acciones"), {'fields': ('crear_venta_desde_boleto_link',)}))
        return fieldsets

    def archivo_boleto_link(self, obj):
        if obj.archivo_boleto:
            return format_html("<a href='{url}'>{name}</a>", url=obj.archivo_boleto.url, name=obj.archivo_boleto.name.split('/')[-1])
        return "-"
    archivo_boleto_link.short_description = _("Archivo")
    
    def crear_venta_desde_boleto_link(self, obj):
        if obj.estado_parseo == 'COM' and not obj.venta_asociada:
            query_params = urlencode({'boleto_id': obj.pk})
            url = reverse('admin:core_venta_add') + '?' + query_params
            return format_html('<a class="button" href="{}">Crear Venta desde Boleto</a>', url)
        elif obj.venta_asociada:
            url_venta = reverse('admin:core_venta_change', args=[obj.venta_asociada.pk])
            return format_html('Venta <a href="{}">{}</a> ya fue creada.', url_venta, obj.venta_asociada.numero_venta)
        else:
            return "El boleto debe ser parseado correctamente primero."
    crear_venta_desde_boleto_link.short_description = "Generar Venta"

    def reintentar_parseo(self, request, queryset):
        for boleto in queryset:
            BoletoImportado.objects.filter(pk=boleto.pk).update(
                estado_parseo=BoletoImportado.EstadoParseo.PENDIENTE,
                log_parseo=_("Reintentando parseo manualmente...")
            )
            self.message_user(request, _("Reintento de parseo iniciado para boleto ID {}.").format(boleto.id_boleto_importado))
    reintentar_parseo.short_description = _("Reintentar parseo de boletos seleccionados")

# Registrar el resto de los modelos CMS para que el admin los conozca
admin.site.register(PaginaCMS)
admin.site.register(DestinoCMS)
admin.site.register(PaqueteTuristicoCMS)
admin.site.register(ArticuloBlog)
admin.site.register(Testimonio)
admin.site.register(MenuItemCMS)
admin.site.register(FormularioContactoCMS)
admin.site.register(Factura)
admin.site.register(ItemFactura)

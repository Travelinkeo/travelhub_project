# Archivo: core/admin.py
import logging

from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.core.files.base import ContentFile
from .services.pdf_service import generar_pdf_factura

from .models import (
    ActividadServicio,
    Agencia,
    AlojamientoReserva,
    AlquilerAutoReserva,
    ArticuloBlog,
    AuditLog,
    BoletoImportado,
    CircuitoDia,
    CircuitoTuristico,
    ComunicacionProveedor,
    DestinoCMS,
    EventoServicio,
    Factura,
    FeeVenta,
    FormularioContactoCMS,
    ItemFactura,
    ItemVenta,
    MenuItemCMS,
    PaginaCMS,
    PagoVenta,
    PaqueteAereo,
    PaqueteTuristicoCMS,
    SegmentoVuelo,
    ServicioAdicionalDetalle,
    Testimonio,
    TrasladoServicio,
    UsuarioAgencia,
    Venta,
    VentaParseMetadata,
)

# Importar admin consolidado de facturación
from . import admin_facturacion_consolidada
from .models.pasaportes import PasaporteEscaneado
from .models.contabilidad import AsientoContable, LiquidacionProveedor, ItemLiquidacion
from .models_catalogos import Aerolinea, Ciudad, Moneda, Pais, ProductoServicio, Proveedor, TipoCambio
from personas.models import Cliente
# No es necesario importar Cotizacion aquí, ya tiene su propio admin.py

# --- Formulario para la acción de facturación ---
class ClienteSelectionForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(),
        label="Seleccionar Cliente para facturar",
        required=True
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

@admin.register(Aerolinea)
class AerolineaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo_iata', 'activa')
    search_fields = ('nombre', 'codigo_iata')
    list_filter = ('activa',)
    ordering = ('nombre',)

# --- Clases Admin para CRM ---





class ComisionProveedorServicioInline(admin.TabularInline):
    model = __import__('core.models_catalogos', fromlist=['ComisionProveedorServicio']).ComisionProveedorServicio
    extra = 1
    fields = ('tipo_servicio', 'comision_porcentaje', 'comision_monto_fijo', 'moneda', 'activo')
    autocomplete_fields = ['moneda']

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rif', 'tipo_proveedor', 'nivel_proveedor', 'fee_nacional', 'fee_internacional', 'activo')
    search_fields = ('nombre', 'rif')
    list_filter = ('tipo_proveedor', 'nivel_proveedor', 'activo')
    inlines = [ComisionProveedorServicioInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'alias', 'rif', 'tipo_proveedor', 'nivel_proveedor', 'activo')
        }),
        ('Fees y Comisiones', {
            'fields': ('fee_nacional', 'fee_internacional')
        }),
        ('Contacto', {
            'fields': ('contacto_nombre', 'contacto_email', 'contacto_telefono', 'direccion', 'ciudad')
        }),
        ('Información Comercial', {
            'fields': ('numero_cuenta_agencia', 'condiciones_pago', 'datos_bancarios', 'notas')
        }),
        ('Identificación GDS', {
            'fields': ('iata', 'seudo_sabre', 'office_id_kiu', 'office_id_amadeus', 'office_id_travelport', 'office_id_hotelbeds', 'office_id_expedia'),
            'classes': ('collapse',)
        }),
        ('Otros Sistemas', {
            'fields': (
                ('otro_sistema_1_nombre', 'otro_sistema_1_id'),
                ('otro_sistema_2_nombre', 'otro_sistema_2_id'),
                ('otro_sistema_3_nombre', 'otro_sistema_3_id'),
                ('otro_sistema_4_nombre', 'otro_sistema_4_id'),
                ('otro_sistema_5_nombre', 'otro_sistema_5_id'),
            ),
            'classes': ('collapse',)
        }),
    )

@admin.register(ProductoServicio)
class ProductoServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_producto', 'proveedor_principal', 'activo')
    search_fields = ('nombre', 'codigo_interno')
    list_filter = ('tipo_producto', 'activo')
    autocomplete_fields = ['proveedor_principal', 'moneda_referencial']

# --- Clases Admin para ERP ---



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

class AlquilerAutoReservaInline(admin.TabularInline):
    model = AlquilerAutoReserva
    extra = 0
    autocomplete_fields = ['proveedor', 'ciudad_retiro', 'ciudad_devolucion']
    fields = ('compania_rentadora', 'categoria_auto', 'fecha_hora_retiro', 'fecha_hora_devolucion', 'ciudad_retiro', 'ciudad_devolucion', 'incluye_seguro', 'numero_confirmacion', 'proveedor')

class ServicioAdicionalDetalleInline(admin.TabularInline):
    model = ServicioAdicionalDetalle
    extra = 0
    autocomplete_fields = ['proveedor']
    fields = ('tipo_servicio', 'descripcion', 'fecha_inicio', 'fecha_fin', 'nombre_pasajero', 'pasaporte_pasajero', 'detalles_cobertura', 'contacto_emergencia', 'participantes', 'operado_por', 'hora_lugar_encuentro', 'duracion_estimada', 'inclusiones_servicio', 'recomendaciones', 'codigo_referencia', 'proveedor')

@admin.register(AsientoContable)
class AsientoContableAdmin(admin.ModelAdmin):
    list_display = ('numero_asiento', 'fecha_contable', 'descripcion_general', 'total_debe', 'total_haber', 'estado')
    search_fields = ('numero_asiento', 'descripcion_general')
    list_filter = ('estado', 'fecha_contable', 'tipo_asiento')
    readonly_fields = ('total_debe', 'total_haber')


class VentaAdminForm(forms.ModelForm):
    boleto_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    class Meta:
        model = Venta
        fields = '__all__'

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    form = VentaAdminForm
    list_display = ('venta_link', 'cliente', 'fecha_venta', 'total_venta', 'estado', 'tipo_venta', 'canal_origen', 'saldo_pendiente')
    list_display_links = ('venta_link',)
    search_fields = ('localizador', 'id_venta', 'cliente__nombres', 'cliente__apellidos')
    list_filter = ('estado', 'fecha_venta', 'tipo_venta', 'canal_origen')
    autocomplete_fields = ['cliente', 'moneda', 'cotizacion_origen', 'asiento_contable_venta']
    inlines = [ItemVentaInline, SegmentoVueloInline, AlojamientoReservaInline, AlquilerAutoReservaInline, ServicioAdicionalDetalleInline, TrasladoServicioInline, ActividadServicioInline, FeeVentaInline, PagoVentaInline]
    readonly_fields = ('total_venta', 'saldo_pendiente', 'boleto_importado_link', 'margen_estimado')
    actions = ['asignar_cliente_y_facturar', 'generar_liquidaciones_proveedor', 'generar_voucher_unificado']

    def venta_link(self, obj):
        url = reverse('admin:core_venta_change', args=[obj.id_venta])
        display_text = obj.localizador or f"Venta #{obj.id_venta}"
        return format_html('<a href="{}">{}</a>', url, display_text)
    venta_link.short_description = "Venta (ID/Localizador)"
    venta_link.admin_order_field = 'localizador'


    def generar_voucher_unificado(self, request, queryset):
        from django.http import HttpResponse
        from django.contrib import messages
        from .services.pdf_service import generar_pdf_voucher_unificado

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
            messages.error(request, f"No se pudo generar el voucher para la Venta {venta.localizador or venta.id_venta}. Revise los logs para más detalles.")

    generar_voucher_unificado.short_description = "Generar Voucher Unificado (PDF)"

    def asignar_cliente_y_facturar(self, request, queryset):
        # Filtramos solo ventas que no tengan cliente y no hayan sido facturadas
        queryset = queryset.filter(cliente__isnull=True, factura__isnull=True)

        if not queryset.exists():
            self.message_user(request, "Las ventas seleccionadas ya tienen un cliente asignado o ya han sido facturadas.", level='warning')
            return

        form = ClienteSelectionForm(request.POST or None)

        if 'apply' in request.POST:
            if form.is_valid():
                cliente = form.cleaned_data['cliente']
                
                facturas_creadas = 0
                for venta in queryset:
                    # 1. Asignar cliente a la Venta
                    venta.cliente = cliente
                    
                    # 2. Crear la Factura
                    factura = Factura.objects.create(
                        cliente=cliente,
                        moneda=venta.moneda,
                        subtotal=venta.subtotal,
                        monto_impuestos=venta.impuestos,
                        # El método save() de Factura recalcula el total
                    )
                    
                    # 3. Copiar los items de la Venta a la Factura
                    for item_venta in venta.items_venta.all():
                        descripcion = item_venta.descripcion_personalizada or item_venta.producto_servicio.nombre
                        
                        # Lógica para enriquecer la descripción
                        if not item_venta.descripcion_personalizada:
                            tipo_producto = item_venta.producto_servicio.tipo_producto
                            if tipo_producto == 'AIR':
                                if BoletoImportado.objects.filter(venta_asociada=venta).count() == 1:
                                    boleto = BoletoImportado.objects.filter(venta_asociada=venta).first()
                                    descripcion = f"Boleto Aéreo: {boleto.ruta_vuelo or ''}"
                                    if boleto.numero_boleto:
                                        descripcion += f" (Tkt: {boleto.numero_boleto})"
                            elif tipo_producto == 'HTL' and venta.alojamientos.count() == 1:
                                alojamiento = venta.alojamientos.first()
                                descripcion = f"Alojamiento: {alojamiento.nombre_establecimiento} en {alojamiento.ciudad.nombre if alojamiento.ciudad else 'N/A'}"
                            elif tipo_producto == 'CAR' and venta.alquileres_autos.count() == 1:
                                alquiler = venta.alquileres_autos.first()
                                descripcion = f"Alquiler de Auto: {alquiler.compania_rentadora or 'N/A'} - {alquiler.categoria_auto or 'N/A'}"
                            elif tipo_producto == 'TRF' and venta.traslados.count() == 1:
                                traslado = venta.traslados.first()
                                descripcion = f"Traslado: {traslado.origen or 'N/A'} a {traslado.destino or 'N/A'}"
                            elif tipo_producto == 'TOU' and venta.actividades.count() == 1:
                                actividad = venta.actividades.first()
                                descripcion = f"Actividad: {actividad.nombre}"
                            elif tipo_producto == 'INS' and venta.servicios_adicionales.filter(tipo_servicio='SEG').count() == 1:
                                seguro = venta.servicios_adicionales.filter(tipo_servicio='SEG').first()
                                descripcion = f"Seguro de Viaje: {seguro.descripcion or 'N/A'}"

                        ItemFactura.objects.create(
                            factura=factura,
                            descripcion=descripcion,
                            cantidad=item_venta.cantidad,
                            precio_unitario=item_venta.precio_unitario_venta
                        )
                    
                    # 4. Enlazar la Venta con su Factura
                    venta.factura = factura
                    venta.save()

                    # 5. Generar y adjuntar el PDF
                    pdf_bytes, pdf_filename = generar_pdf_factura(factura.pk)
                    if pdf_bytes and pdf_filename:
                        factura.archivo_pdf.save(pdf_filename, ContentFile(pdf_bytes), save=True)

                    facturas_creadas += 1

                self.message_user(request, f"{facturas_creadas} factura(s) generada(s) exitosamente.")
                return HttpResponseRedirect(request.get_full_path())

        context = {
            'ventas': queryset,
            'cliente_form': form,
            'title': 'Asignar Cliente y Facturar',
            'opts': self.model._meta,
        }
        return render(request, 'admin/asignar_cliente_y_facturar.html', context)
    asignar_cliente_y_facturar.short_description = "Asignar Cliente y Generar Factura"

    def generar_liquidaciones_proveedor(self, request, queryset):
        from collections import defaultdict

        liquidaciones_creadas = 0
        for venta in queryset:
            items_por_proveedor = defaultdict(list)
            for item in venta.items_venta.all():
                if item.proveedor_servicio and item.costo_neto_proveedor is not None:
                    items_por_proveedor[item.proveedor_servicio].append(item)

            for proveedor, items in items_por_proveedor.items():
                # Evitar duplicados
                if LiquidacionProveedor.objects.filter(proveedor=proveedor, venta=venta).exists():
                    continue

                monto_total_a_pagar = 0
                items_a_liquidar = []

                for item in items:
                    costo = item.costo_neto_proveedor or 0
                    fee = item.fee_proveedor or 0
                    comision = item.comision_agencia_monto or 0
                    
                    monto_item = (costo + fee) - comision
                    monto_total_a_pagar += monto_item
                    items_a_liquidar.append((item, monto_item))

                if monto_total_a_pagar > 0:
                    liquidacion = LiquidacionProveedor.objects.create(
                        proveedor=proveedor,
                        venta=venta,
                        monto_total=monto_total_a_pagar
                    )
                    
                    for item_venta, monto_a_pagar_item in items_a_liquidar:
                        ItemLiquidacion.objects.create(
                            liquidacion=liquidacion,
                            item_venta=item_venta,
                            descripcion=f"Liquidación por: {item_venta.descripcion_personalizada}",
                            monto=monto_a_pagar_item
                        )
                    
                    liquidaciones_creadas += 1

        if liquidaciones_creadas > 0:
            self.message_user(request, f"Se generaron {liquidaciones_creadas} liquidaciones a proveedores.")
        else:
            self.message_user(request, "No se generaron nuevas liquidaciones. Verifique que las ventas tengan proveedores, costos asignados y que no exista una liquidación previa para esa venta/proveedor.", level='warning')
    generar_liquidaciones_proveedor.short_description = "Generar Liquidación a Proveedor(es)"

    def generar_liquidaciones_proveedor(self, request, queryset):
        from collections import defaultdict

        liquidaciones_creadas = 0
        for venta in queryset:
            items_por_proveedor = defaultdict(list)
            for item in venta.items_venta.all():
                if item.proveedor_servicio and item.costo_neto_proveedor is not None:
                    items_por_proveedor[item.proveedor_servicio].append(item)

            for proveedor, items in items_por_proveedor.items():
                # Evitar duplicados
                if LiquidacionProveedor.objects.filter(proveedor=proveedor, venta=venta).exists():
                    continue

                monto_total_a_pagar = 0
                items_a_liquidar = []

                for item in items:
                    costo = item.costo_neto_proveedor or 0
                    fee = item.fee_proveedor or 0
                    comision = item.comision_agencia_monto or 0
                    
                    monto_item = (costo + fee) - comision
                    monto_total_a_pagar += monto_item
                    items_a_liquidar.append((item, monto_item))

                if monto_total_a_pagar > 0:
                    liquidacion = LiquidacionProveedor.objects.create(
                        proveedor=proveedor,
                        venta=venta,
                        monto_total=monto_total_a_pagar
                    )
                    
                    for item_venta, monto_a_pagar_item in items_a_liquidar:
                        ItemLiquidacion.objects.create(
                            liquidacion=liquidacion,
                            item_venta=item_venta,
                            descripcion=f"Liquidación por: {item_venta.descripcion_personalizada}",
                            monto=monto_a_pagar_item
                        )
                    
                    liquidaciones_creadas += 1

        if liquidaciones_creadas > 0:
            self.message_user(request, f"Se generaron {liquidaciones_creadas} liquidaciones a proveedores.")
        else:
            self.message_user(request, "No se generaron nuevas liquidaciones. Verifique que las ventas tengan proveedores, costos asignados y que no exista una liquidación previa para esa venta/proveedor.", level='warning')
    generar_liquidaciones_proveedor.short_description = "Generar Liquidación a Proveedor(es)"

    def boleto_importado_link(self, obj):
        boleto = BoletoImportado.objects.filter(venta_asociada=obj).first()
        if boleto:
            url = reverse('admin:core_boletoimportado_change', args=[boleto.pk])
            return format_html('<a href="{}">Ver Boleto Original (ID: {})</a>', url, boleto.pk)
        return "N/A (Creada manually)"
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
                
                if cliente:
                    initial['cliente'] = cliente.pk
                
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
    list_display = ('id_boleto_importado', 'archivo_boleto_link', 'pdf_generado_link', 'fecha_subida', 'estado_parseo', 'numero_boleto', 'nombre_pasajero_procesado', 'venta_asociada')
    search_fields = ('archivo_boleto', 'numero_boleto', 'nombre_pasajero_completo')
    list_filter = ('estado_parseo', 'formato_detectado', 'fecha_subida')
    readonly_fields = (
        'fecha_subida', 'formato_detectado', 'datos_parseados', 'estado_parseo', 'log_parseo', 
        'numero_boleto', 'nombre_pasajero_completo', 'nombre_pasajero_procesado', 
        'ruta_vuelo', 'fecha_emision_boleto', 'aerolinea_emisora', 'direccion_aerolinea',
        'agente_emisor', 'foid_pasajero', 'localizador_pnr', 'tarifa_base', 
        'impuestos_descripcion', 'impuestos_total_calculado', 'total_boleto', 'crear_venta_desde_boleto_link',
        'pdf_generado_link'  # Añadido aquí
    )
    actions = ['reintentar_parseo']
    autocomplete_fields = ['venta_asociada']
    

    
    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (None, {'fields': ('archivo_boleto', 'venta_asociada')}),
            (_("Información de Parseo (Automático)"), {'fields': ('estado_parseo', 'log_parseo', 'datos_parseados', 'pdf_generado_link')}),
            (_("Datos Extraídos"), {'fields': ('numero_boleto', 'nombre_pasajero_procesado', 'total_boleto', 'localizador_pnr')}),
        ]
        if obj and (obj.estado_parseo == 'COM' or obj.venta_asociada):
            fieldsets.append((_("Acciones"), {'fields': ('crear_venta_desde_boleto_link',)}))
        return fieldsets

    def archivo_boleto_link(self, obj):
        if obj.archivo_boleto:
            return format_html("<a href='{url}'>{name}</a>", url=obj.archivo_boleto.url, name=obj.archivo_boleto.name.split('/')[-1])
        return "-"
    archivo_boleto_link.short_description = _("Archivo Original")

    def pdf_generado_link(self, obj):
        url = obj.get_pdf_url()
        if url:
            return format_html('<a href="{}" target="_blank" class="button">📄 Ver PDF</a>', url)
        return "No generado"
    pdf_generado_link.short_description = "PDF Generado"
    
    def crear_venta_desde_boleto_link(self, obj):
        if obj.estado_parseo == 'COM' and not obj.venta_asociada:
            query_params = urlencode({'boleto_id': obj.pk})
            url = reverse('admin:core_venta_add') + '?' + query_params
            return format_html('<a class="button" href="{}">Crear Venta desde Boleto</a>', url)
        elif obj.venta_asociada:
            url_venta = reverse('admin:core_venta_change', args=[obj.venta_asociada.pk])
            # El modelo Venta no posee campo numero_venta; usamos localizador si existe o el id_venta como fallback.
            identificador = getattr(obj.venta_asociada, 'localizador', None) or getattr(obj.venta_asociada, 'id_venta', obj.venta_asociada.pk)
            return format_html('Venta <a href="{}">{}</a> ya fue creada.', url_venta, identificador)
        else:
            return "El boleto debe ser parseado correctamente primero."
    crear_venta_desde_boleto_link.short_description = "Generar Venta"

    def reintentar_parseo(self, request, queryset):
        for boleto in queryset:
            BoletoImportado.objects.filter(pk=boleto.pk).update(
                estado_parseo=BoletoImportado.EstadoParseo.PENDIENTE,
                log_parseo=_("Reintentando parseo manualmente...")
            )
            # Tolerar ausencia del framework de mensajes en contextos de prueba.
            try:
                self.message_user(request, _("Reintento de parseo iniciado para boleto ID {}.").format(boleto.id_boleto_importado))
            except Exception as e:
                # In some test contexts, message_user may not be available.
                # We log this as a warning instead of crashing.
                logging.warning(f"Could not send admin message during re-parse action: {e}")
    reintentar_parseo.short_description = _("Reintentar parseo de boletos seleccionados")

# Registrar el resto de los modelos CMS para que el admin los conozca
admin.site.register(PaginaCMS)
admin.site.register(DestinoCMS)
admin.site.register(PaqueteTuristicoCMS)
admin.site.register(ArticuloBlog)
admin.site.register(Testimonio)
admin.site.register(MenuItemCMS)
admin.site.register(FormularioContactoCMS)
# Factura antigua deprecada - usar FacturaConsolidada en admin_facturacion_consolidada.py

# ItemFactura ya no se registra - usar ItemFacturaConsolidada

class ItemLiquidacionInline(admin.TabularInline):
    model = ItemLiquidacion
    extra = 0
    readonly_fields = ('item_venta', 'descripcion', 'monto')
    can_delete = False
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(LiquidacionProveedor)
class LiquidacionProveedorAdmin(admin.ModelAdmin):
    list_display = ('id_liquidacion', 'proveedor', 'venta', 'fecha_emision', 'monto_total', 'saldo_pendiente', 'estado')
    list_filter = ('estado', 'proveedor', 'fecha_emision')
    search_fields = ('id_liquidacion', 'venta__localizador', 'proveedor__nombre')
    inlines = [ItemLiquidacionInline]
    readonly_fields = ('saldo_pendiente', 'monto_total', 'proveedor', 'venta')


@admin.register(VentaParseMetadata)
class VentaParseMetadataAdmin(admin.ModelAdmin):
    list_display = ('id_metadata','venta','fuente','currency','total_amount','amount_consistency','creado')
    list_filter = ('fuente','currency','amount_consistency','creado')
    search_fields = ('venta__localizador',)
    readonly_fields = ('raw_normalized_json','segments_json','creado')

@admin.register(AlquilerAutoReserva)
class AlquilerAutoReservaAdmin(admin.ModelAdmin):
    list_display = ('id_alquiler_auto','venta','categoria_auto','compania_rentadora','fecha_hora_retiro','fecha_hora_devolucion','incluye_seguro')
    search_fields = ('numero_confirmacion','compania_rentadora')
    list_filter = ('incluye_seguro','compania_rentadora')
    autocomplete_fields = ['venta','proveedor','ciudad_retiro','ciudad_devolucion']

@admin.register(EventoServicio)
class EventoServicioAdmin(admin.ModelAdmin):
    list_display = ('id_evento_servicio','venta','nombre_evento','fecha_evento','ubicacion','zona_asiento')
    search_fields = ('nombre_evento','codigo_boleto_evento')
    list_filter = ('fecha_evento',)
    autocomplete_fields = ['venta','proveedor']

class CircuitoDiaInline(admin.TabularInline):
    model = CircuitoDia
    extra = 0
    autocomplete_fields = ['ciudad']

@admin.register(CircuitoTuristico)
class CircuitoTuristicoAdmin(admin.ModelAdmin):
    list_display = ('id_circuito','venta','nombre_circuito','fecha_inicio','fecha_fin','dias_total')
    search_fields = ('nombre_circuito',)
    list_filter = ('fecha_inicio',)
    inlines = [CircuitoDiaInline]
    autocomplete_fields = ['venta']

@admin.register(PaqueteAereo)
class PaqueteAereoAdmin(admin.ModelAdmin):
    list_display = ('id_paquete_aereo','venta','nombre_paquete','incluye_vuelos','incluye_hotel','noches','pasajeros')
    list_filter = ('incluye_vuelos','incluye_hotel')
    search_fields = ('nombre_paquete',)
    autocomplete_fields = ['venta']

@admin.register(ServicioAdicionalDetalle)
class ServicioAdicionalDetalleAdmin(admin.ModelAdmin):
    list_display = ('id_servicio_adicional','venta','tipo_servicio','codigo_referencia','fecha_inicio','fecha_fin')
    list_filter = ('tipo_servicio',)
    search_fields = ('codigo_referencia',)
    autocomplete_fields = ['venta','proveedor']
    actions = ['generar_voucher_servicio']
    
    def generar_voucher_servicio(self, request, queryset):
        from django.http import HttpResponse
        from django.contrib import messages
        from .services.voucher_service import generar_voucher_servicio
        
        if queryset.count() != 1:
            messages.error(request, "Seleccione exactamente un servicio para generar el voucher.")
            return
        
        servicio = queryset.first()
        try:
            pdf_bytes, filename = generar_voucher_servicio(servicio)
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            messages.error(request, f"Error al generar voucher: {str(e)}")
    
    generar_voucher_servicio.short_description = "Generar Voucher (PDF)"

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id_audit_log','modelo','object_id','accion','venta','creado')
    list_filter = ('modelo','accion','creado')
    search_fields = ('modelo','object_id','venta__localizador','descripcion')
    readonly_fields = ('modelo','object_id','accion','venta','descripcion','datos_previos','datos_nuevos','metadata_extra','creado')
    ordering = ('-creado',)

@admin.register(ComunicacionProveedor)
class ComunicacionProveedorAdmin(admin.ModelAdmin):
    list_display = ('asunto', 'remitente', 'categoria', 'fecha_recepcion')
    list_filter = ('categoria', 'remitente', 'fecha_recepcion')
    search_fields = ('asunto', 'remitente', 'cuerpo_completo')
    readonly_fields = ('remitente', 'asunto', 'fecha_recepcion', 'categoria', 'contenido_extraido', 'cuerpo_completo')
    ordering = ('-fecha_recepcion',)

# --- Admin para Agencia (Multi-tenant) ---

@admin.register(Agencia)
class AgenciaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'rif', 'iata', 'email_principal', 'activa', 'fecha_creacion']
    list_filter = ['activa', 'pais', 'fecha_creacion']
    search_fields = ['nombre', 'nombre_comercial', 'rif', 'iata', 'email_principal']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'nombre_comercial', 'rif', 'iata', 'propietario', 'activa')
        }),
        ('Contacto', {
            'fields': ('telefono_principal', 'telefono_secundario', 'email_principal', 'email_soporte', 'email_ventas')
        }),
        ('Dirección', {
            'fields': ('direccion', 'ciudad', 'estado', 'pais', 'codigo_postal')
        }),
        ('Branding', {
            'fields': ('logo', 'logo_secundario', 'color_primario', 'color_secundario')
        }),
        ('Redes Sociales', {
            'fields': ('website', 'facebook', 'instagram', 'twitter', 'whatsapp')
        }),
        ('Configuración', {
            'fields': ('moneda_principal', 'timezone', 'idioma')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion')
        }),
    )

@admin.register(UsuarioAgencia)
class UsuarioAgenciaAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'agencia', 'rol', 'activo', 'fecha_asignacion']
    list_filter = ['rol', 'activo', 'agencia']
    search_fields = ['usuario__username', 'usuario__email', 'agencia__nombre']
    readonly_fields = ['fecha_asignacion']

# Registrar Retenciones ISLR
from .models.retenciones_islr import RetencionISLR

@admin.register(RetencionISLR)
class RetencionISLRAdmin(admin.ModelAdmin):
    list_display = ['numero_comprobante', 'fecha_emision', 'cliente', 'factura',
                   'base_imponible', 'porcentaje_retencion', 'monto_retenido', 'estado']
    list_filter = ['estado', 'tipo_operacion', 'periodo_fiscal']
    search_fields = ['numero_comprobante', 'cliente__nombres', 'factura__numero_factura']
    readonly_fields = ['monto_retenido', 'creado', 'actualizado']
    autocomplete_fields = ['factura', 'cliente']

@admin.register(PasaporteEscaneado)
class PasaporteEscaneadoAdmin(admin.ModelAdmin):
    list_display = ('numero_pasaporte', 'nombre_completo', 'nacionalidad', 'confianza_ocr', 'fecha_procesamiento', 'verificado_manualmente')
    list_filter = ('confianza_ocr', 'nacionalidad', 'verificado_manualmente', 'fecha_procesamiento')
    search_fields = ('numero_pasaporte', 'nombres', 'apellidos')
    readonly_fields = ('fecha_procesamiento', 'datos_ocr_completos', 'texto_mrz', 'es_valido')
    autocomplete_fields = ['cliente']
    actions = ['marcar_como_verificado', 'crear_clientes_desde_pasaportes']
    fields = ('imagen_original', 'cliente', 'numero_pasaporte', 'nombres', 'apellidos', 'nacionalidad', 'fecha_nacimiento', 'fecha_vencimiento', 'sexo', 'confianza_ocr', 'verificado_manualmente')
    
    def marcar_como_verificado(self, request, queryset):
        updated = queryset.update(verificado_manualmente=True)
        self.message_user(request, f'{updated} pasaporte(s) marcado(s) como verificado(s) manualmente.')
    marcar_como_verificado.short_description = 'Marcar como verificado manualmente'
    
    def crear_clientes_desde_pasaportes(self, request, queryset):
        created = 0
        updated = 0
        for pasaporte in queryset.filter(cliente__isnull=True):
            if pasaporte.es_valido:
                existing_client = Cliente.objects.filter(
                    numero_documento=pasaporte.numero_pasaporte
                ).first()
                
                if existing_client:
                    client_data = pasaporte.to_cliente_data()
                    for key, value in client_data.items():
                        if value:
                            setattr(existing_client, key, value)
                    existing_client.save()
                    pasaporte.cliente = existing_client
                    pasaporte.save()
                    updated += 1
                else:
                    client_data = pasaporte.to_cliente_data()
                    nuevo_cliente = Cliente.objects.create(**client_data)
                    pasaporte.cliente = nuevo_cliente
                    pasaporte.save()
                    created += 1
        
        message = f'Creados: {created} cliente(s), Actualizados: {updated} cliente(s)'
        self.message_user(request, message)
    crear_clientes_desde_pasaportes.short_description = 'Crear/actualizar clientes desde pasaportes válidos'
    
    def save_model(self, request, obj, form, change):
        if not obj.procesado_por:
            obj.procesado_por = request.user
        super().save_model(request, obj, form, change)

# Importar admin de tarifario de hoteles
from . import admin_tarifario
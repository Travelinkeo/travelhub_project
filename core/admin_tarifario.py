from django.contrib import admin
from core.admin_saas import SaaSAdminMixin
from core.models import TarifarioProveedor, HotelTarifario, TipoHabitacion, TarifaHabitacion, Amenity, ImagenHotel

class TarifaHabitacionInline(admin.TabularInline):
    model = TarifaHabitacion
    extra = 1
    fields = ['fecha_inicio', 'fecha_fin', 'nombre_temporada', 'moneda', 'tipo_tarifa', 'tarifa_sgl', 'tarifa_dbl', 'tarifa_tpl', 'tarifa_cpl', 'tarifa_nino']

class TipoHabitacionInline(admin.TabularInline):
    model = TipoHabitacion
    extra = 1
    fields = ['nombre', 'capacidad_adultos', 'capacidad_ninos', 'capacidad_total', 'edit_rates_link']
    readonly_fields = ['edit_rates_link']

    def edit_rates_link(self, obj):
        if obj.id:
            from django.urls import reverse
            from django.utils.html import format_html
            url = reverse('admin:core_tipohabitacion_change', args=[obj.id])
            return format_html('<a href="{}" target="_blank" class="button" style="background-color: #4f46e5; color: white; padding: 4px 8px; border-radius: 4px;">Gestionar Tarifas</a>', url)
        return "-"
    edit_rates_link.short_description = "Tarifas"

class ImagenHotelInline(admin.TabularInline):
    model = ImagenHotel
    extra = 2
    fields = ['imagen', 'titulo', 'tipo', 'es_portada']

@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'icono_lucide']
    search_fields = ['nombre']

@admin.register(TarifarioProveedor)
class TarifarioProveedorAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = 'proveedor__agencia'
    list_display = ['id', 'nombre', 'proveedor', 'fecha_vigencia_inicio', 'fecha_vigencia_fin', 'comision_estandar', 'activo']
    list_filter = ['activo', 'proveedor']
    search_fields = ['nombre']

@admin.register(HotelTarifario)
class HotelTarifarioAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = 'tarifario__proveedor__agencia'
    list_display = ['nombre', 'destino', 'categoria', 'regimen_default', 'activo', 'destacado']
    list_filter = ['activo', 'destacado', 'destino', 'categoria']
    search_fields = ['nombre', 'destino', 'descripcion_larga']
    prepopulated_fields = {'slug': ('nombre', 'destino')}
    filter_horizontal = ['amenidades']
    inlines = [ImagenHotelInline, TipoHabitacionInline]
    
    fieldsets = [
        ('Información Principal', {
            'fields': ['tarifario', 'nombre', 'slug', 'destino', 'imagen_principal', 'logo', 'video_promocional', 'categoria']
        }),
        ('Detalles y Geolocalización', {
            'fields': ['descripcion_corta', 'descripcion_larga', 'direccion', 'coordenadas_mapa']
        }),
        ('Servicios', {
            'fields': ['amenidades']
        }),
        ('Operativo', {
            'fields': ['regimen_default', 'comision', 'politicas']
        }),
        ('Configuración', {
            'fields': ['check_in', 'check_out', 'activo', 'destacado']
        }),
    ]

@admin.register(TarifaHabitacion)
class TarifaHabitacionAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = 'tipo_habitacion__hotel__tarifario__proveedor__agencia'
    list_display = ['tipo_habitacion', 'fecha_inicio', 'fecha_fin', 'moneda', 'tarifa_sgl', 'tarifa_dbl']
    list_filter = ['moneda', 'tipo_habitacion__hotel']
    search_fields = ['tipo_habitacion__nombre', 'tipo_habitacion__hotel__nombre']

@admin.register(TipoHabitacion)
class TipoHabitacionAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = 'hotel__tarifario__proveedor__agencia'
    """
    Permite editar las tarifas directamente dentro del Tipo de Habitación.
    Esto acerca la experiencia a 'un solo formulario' (Hotel -> Habitaciones -> Tarifas).
    """
    list_display = ['nombre', 'hotel', 'capacidad_total']
    list_filter = ['hotel']
    search_fields = ['nombre', 'hotel__nombre']
    inlines = [TarifaHabitacionInline]
    autocomplete_fields = ['hotel']

from django.contrib import admin
from core.models import TarifarioProveedor, HotelTarifario, TipoHabitacion, TarifaHabitacion


class TarifaHabitacionInline(admin.TabularInline):
    model = TarifaHabitacion
    extra = 1
    fields = ['fecha_inicio', 'fecha_fin', 'nombre_temporada', 'moneda', 'tipo_tarifa', 'tarifa_sgl', 'tarifa_dbl', 'tarifa_tpl']


class TipoHabitacionInline(admin.TabularInline):
    model = TipoHabitacion
    extra = 1
    fields = ['nombre', 'capacidad_adultos', 'capacidad_ninos', 'capacidad_total']


@admin.register(TarifarioProveedor)
class TarifarioProveedorAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'proveedor', 'fecha_vigencia_inicio', 'fecha_vigencia_fin', 'comision_estandar', 'activo', 'fecha_carga']
    list_filter = ['activo', 'proveedor', 'fecha_vigencia_inicio']
    search_fields = ['nombre', 'proveedor__nombre']
    date_hierarchy = 'fecha_carga'
    readonly_fields = ['fecha_carga']


@admin.register(HotelTarifario)
class HotelTarifarioAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'destino', 'regimen', 'comision', 'tarifario', 'activo']
    list_filter = ['activo', 'destino', 'regimen', 'tarifario']
    search_fields = ['nombre', 'destino', 'ubicacion_descripcion']
    inlines = [TipoHabitacionInline]
    fieldsets = [
        ('Información Básica', {
            'fields': ['tarifario', 'nombre', 'destino', 'ubicacion_descripcion', 'regimen', 'comision']
        }),
        ('Políticas', {
            'fields': ['politicas', 'check_in', 'check_out', 'minimo_noches_temporada_baja', 'minimo_noches_temporada_alta']
        }),
        ('Estado', {
            'fields': ['activo']
        }),
    ]


@admin.register(TipoHabitacion)
class TipoHabitacionAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'hotel', 'capacidad_adultos', 'capacidad_ninos', 'capacidad_total']
    list_filter = ['hotel__destino', 'hotel']
    search_fields = ['nombre', 'hotel__nombre']
    inlines = [TarifaHabitacionInline]


@admin.register(TarifaHabitacion)
class TarifaHabitacionAdmin(admin.ModelAdmin):
    list_display = ['tipo_habitacion', 'fecha_inicio', 'fecha_fin', 'nombre_temporada', 'moneda', 'tipo_tarifa', 'tarifa_sgl', 'tarifa_dbl', 'tarifa_tpl']
    list_filter = ['moneda', 'tipo_tarifa', 'tipo_habitacion__hotel__destino', 'fecha_inicio', 'nombre_temporada']
    search_fields = ['tipo_habitacion__nombre', 'tipo_habitacion__hotel__nombre', 'nombre_temporada']
    date_hierarchy = 'fecha_inicio'
    fieldsets = [
        ('Vigencia', {
            'fields': ['tipo_habitacion', 'fecha_inicio', 'fecha_fin', 'nombre_temporada']
        }),
        ('Configuración de Tarifa', {
            'fields': ['moneda', 'tipo_tarifa']
        }),
        ('Tarifas por Ocupación', {
            'fields': ['tarifa_sgl', 'tarifa_dbl', 'tarifa_tpl']
        }),
    ]

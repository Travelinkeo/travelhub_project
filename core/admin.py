import logging

from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline

from apps.common.models import Aerolinea, Ciudad, Moneda, Pais

# Importar inlines compartidos
from .models import (
    Agencia,
    AgenciaBranding,
    AgenciaConfiguracion,
    UsuarioAgencia,
)

logger = logging.getLogger(__name__)

# --- Clases Admin para Configuración Global (Catálogos) ---


@admin.register(Pais)
class PaisAdmin(ModelAdmin):
    list_display = ("nombre", "codigo_iso_2", "codigo_iso_3")
    search_fields = ("nombre", "codigo_iso_2", "codigo_iso_3")


@admin.register(Ciudad)
class CiudadAdmin(ModelAdmin):
    list_display = ("nombre", "pais", "codigo_iata")
    search_fields = ("nombre", "codigo_iata", "pais__nombre")
    list_filter = ("pais",)
    autocomplete_fields = ["pais"]


@admin.register(Moneda)
class MonedaAdmin(ModelAdmin):
    list_display = ("nombre", "codigo_iso", "simbolo", "es_moneda_local")
    search_fields = ("nombre", "codigo_iso")
    list_filter = ("es_moneda_local",)


@admin.register(Aerolinea)
class AerolineaAdmin(ModelAdmin):
    list_display = ("nombre", "codigo_iata", "activa")
    search_fields = ("nombre", "codigo_iata")
    list_filter = ("activa",)
    ordering = ("nombre",)


# @admin.register(Proveedor)
# class ProveedorAdmin(SaaSAdminMixin, admin.ModelAdmin):
#     list_display = ('nombre', 'rif', 'tipo_proveedor', 'nivel_proveedor', 'activo')
#     search_fields = ('nombre', 'rif')
#     list_filter = ('tipo_proveedor', 'nivel_proveedor', 'activo')

#     fieldsets = (
#         ('Información Básica', {
#             'fields': ('nombre', 'rif', 'tipo_proveedor', 'nivel_proveedor', 'activo')
#         }),
#         ('Contacto', {
#             'fields': ('contacto_nombre', 'contacto_email', 'contacto_telefono', 'direccion', 'ciudad')
#         }),
#         ('GDS / Conectividad', {
#             'fields': ('iata', 'seudo_sabre', 'office_id_kiu', 'office_id_amadeus', 'office_id_travelport', 'office_id_hotelbeds', 'office_id_expedia'),
#             'classes': ('collapse',)
#         }),
#     )

# @admin.register(ProductoServicio)
# class ProductoServicioAdmin(SaaSAdminMixin, admin.ModelAdmin):
#     saas_agency_field = 'proveedor_principal__agencia'
#     list_display = ('nombre', 'tipo_producto', 'proveedor_principal', 'activo')
#     search_fields = ('nombre',)
#     list_filter = ('tipo_producto', 'activo')
#     autocomplete_fields = ['proveedor_principal', 'moneda_referencial']


# --- SaaS / Multi-tenant ---
class AgenciaBrandingInline(StackedInline):
    model = AgenciaBranding
    can_delete = False
    verbose_name_plural = "Branding y Assets"


class AgenciaConfiguracionInline(StackedInline):
    model = AgenciaConfiguracion
    can_delete = False
    verbose_name_plural = "Configuración de Negocio y SaaS"


@admin.register(Agencia)
class AgenciaAdmin(ModelAdmin):
    list_display = ["nombre", "rif", "iata", "email_principal", "activa"]
    list_filter = ["activa", "pais"]
    search_fields = ["nombre", "rif", "iata"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    inlines = [AgenciaBrandingInline, AgenciaConfiguracionInline]

    def get_readonly_fields(self, request, obj=None):
        # DOCTRINA ANTIGRAVITY: Solo superusuarios pueden cambiar el RIF o IATA de una agencia
        if not request.user.is_superuser:
            return self.readonly_fields + ["rif", "iata"]
        return self.readonly_fields


@admin.register(AgenciaBranding)
class AgenciaBrandingAdmin(ModelAdmin):
    list_display = ["agencia_master", "ui_theme", "color_primario"]
    search_fields = ["agencia_master__nombre"]


@admin.register(AgenciaConfiguracion)
class AgenciaConfiguracionAdmin(ModelAdmin):
    list_display = ["agencia_master", "plan", "subdominio_slug"]
    search_fields = ["agencia_master__nombre", "subdominio_slug"]


@admin.register(UsuarioAgencia)
class UsuarioAgenciaAdmin(ModelAdmin):
    list_display = ["usuario", "agencia", "rol", "activo"]
    list_filter = ["rol", "activo", "agencia"]
    autocomplete_fields = ["usuario", "agencia"]

    def get_readonly_fields(self, request, obj=None):
        # Evitar escalada de privilegios: Solo superusuarios pueden cambiar roles
        if not request.user.is_superuser:
            return ["usuario", "agencia", "rol"]
        return []


# --- Admin Importados (y Activados) ---
# from core import admin_facturacion_consolidada
# from core import admin_tarifario

# @admin.register(CruceroReserva)
# class CruceroReservaAdmin(SaaSAdminMixin, admin.ModelAdmin):
#     saas_agency_field = 'venta__agencia'
#     list_display = ['nombre_crucero', 'naviera', 'fecha_embarque', 'venta']
#     search_fields = ['nombre_crucero', 'naviera']
#     list_filter = ['naviera', 'fecha_embarque']
#     autocomplete_fields = ['venta', 'proveedor', 'moneda']

# @admin.register(RetencionISLR)
# class RetencionISLRAdmin(admin.ModelAdmin):
#     list_display = ['numero_comprobante', 'fecha_emision', 'cliente', 'estado']
#     list_filter = ['estado', 'periodo_fiscal']
#     autocomplete_fields = ['factura', 'cliente']

# @admin.register(FeatureFlag)
# class FeatureFlagAdmin(admin.ModelAdmin):
#     list_display = ['nombre', 'agencia', 'enabled', 'rollout_percentage', 'updated_at']
#     list_filter = ['enabled', 'agencia']
#     search_fields = ['nombre', 'description']
#     list_editable = ['enabled', 'rollout_percentage']

# @admin.register(CronApiKey)
# class CronApiKeyAdmin(admin.ModelAdmin):
#     list_display = ['name', 'prefix', 'is_active', 'last_used', 'expires_at', 'agencia']
#     list_filter = ['is_active', 'agencia']
#     search_fields = ['name']
#     readonly_fields = ['key_hash', 'prefix', 'last_used']

# Nota: Los modelos de negocio (Venta, Boleto, Factura, Cliente) están en sus propias aplicaciones.

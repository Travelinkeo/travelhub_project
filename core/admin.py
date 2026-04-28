# Archivo: core/admin.py
import logging
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Agencia, UsuarioAgencia
from .models_catalogos import Aerolinea, Ciudad, Moneda, Pais, ProductoServicio, Proveedor, TipoCambio
from .models.retenciones_islr import RetencionISLR
from .models.retenciones_islr import RetencionISLR
from .models.cruceros import CruceroReserva
from .admin_saas import SaaSAdminMixin

# Importar inlines compartidos
from .admin_migration import MigrationCheckInline, validate_migration_requirements_action

logger = logging.getLogger(__name__)

# --- Clases Admin para Configuración Global (Catálogos) ---

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

@admin.register(Aerolinea)
class AerolineaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo_iata', 'activa')
    search_fields = ('nombre', 'codigo_iata')
    list_filter = ('activa',)
    ordering = ('nombre',)

@admin.register(Proveedor)
class ProveedorAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ('nombre', 'rif', 'tipo_proveedor', 'nivel_proveedor', 'activo')
    search_fields = ('nombre', 'rif')
    list_filter = ('tipo_proveedor', 'nivel_proveedor', 'activo')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'rif', 'tipo_proveedor', 'nivel_proveedor', 'activo')
        }),
        ('Contacto', {
            'fields': ('contacto_nombre', 'contacto_email', 'contacto_telefono', 'direccion', 'ciudad')
        }),
        ('GDS / Conectividad', {
            'fields': ('iata', 'seudo_sabre', 'office_id_kiu', 'office_id_amadeus'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ProductoServicio)
class ProductoServicioAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = 'proveedor_principal__agencia'
    list_display = ('nombre', 'tipo_producto', 'proveedor_principal', 'activo')
    search_fields = ('nombre',)
    list_filter = ('tipo_producto', 'activo')
    autocomplete_fields = ['proveedor_principal', 'moneda_referencial']

# --- SaaS / Multi-tenant ---

@admin.register(Agencia)
class AgenciaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'rif', 'iata', 'email_principal', 'activa']
    list_filter = ['activa', 'pais']
    search_fields = ['nombre', 'rif', 'iata']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']

    def get_readonly_fields(self, request, obj=None):
        # DOCTRINA ANTIGRAVITY: Solo superusuarios pueden cambiar el RIF o IATA de una agencia
        if not request.user.is_superuser:
            return self.readonly_fields + ['rif', 'iata']
        return self.readonly_fields

@admin.register(UsuarioAgencia)
class UsuarioAgenciaAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'agencia', 'rol', 'activo']
    list_filter = ['rol', 'activo', 'agencia']
    autocomplete_fields = ['usuario', 'agencia']

    def get_readonly_fields(self, request, obj=None):
        # Evitar escalada de privilegios: Solo superusuarios pueden cambiar roles
        if not request.user.is_superuser:
            return ['usuario', 'agencia', 'rol']
        return []

# --- Admin Importados (y Activados) ---
from core import admin_facturacion_consolidada
from core import admin_tarifario

@admin.register(CruceroReserva)
class CruceroReservaAdmin(SaaSAdminMixin, admin.ModelAdmin):
    saas_agency_field = 'venta__agencia'
    list_display = ['nombre_crucero', 'naviera', 'fecha_embarque', 'venta']
    search_fields = ['nombre_crucero', 'naviera']
    list_filter = ['naviera', 'fecha_embarque']
    autocomplete_fields = ['venta', 'proveedor', 'moneda']

@admin.register(RetencionISLR)
class RetencionISLRAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ['numero_comprobante', 'fecha_emision', 'cliente', 'estado']
    list_filter = ['estado', 'periodo_fiscal']
    autocomplete_fields = ['factura', 'cliente']

# Nota: Los modelos de negocio (Venta, Boleto, Factura, Cliente) están en sus propias aplicaciones.

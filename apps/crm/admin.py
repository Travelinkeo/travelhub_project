from django.contrib import admin
from core.admin_saas import SaaSAdminMixin
from .models import Cliente, Pasajero

@admin.register(Pasajero)
class PasajeroAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'tipo_documento', 'numero_documento', 'email')
    search_fields = ('nombres', 'apellidos', 'numero_documento', 'email')
    list_filter = ('tipo_documento',)

@admin.register(Cliente)
class ClienteAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'nombre_empresa', 'tipo_cliente', 'telefono_principal', 'email')
    search_fields = ('nombres', 'apellidos', 'nombre_empresa', 'email', 'telefono_principal')
    list_filter = ('tipo_cliente', 'es_cliente_frecuente')
    ordering = ('apellidos', 'nombres')
    autocomplete_fields = ['ciudad', 'pais_emision_pasaporte', 'nacionalidad']
    filter_horizontal = ('pasajeros',)

from django.contrib import admin
from .models import Cliente, Pasajero

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('get_nombre_completo', 'cedula_identidad', 'email', 'telefono_principal', 'tipo_cliente')
    search_fields = ('nombres', 'apellidos', 'cedula_identidad', 'nombre_empresa', 'email')
    list_filter = ('tipo_cliente',)
    autocomplete_fields = ['ciudad', 'pais_emision_pasaporte', 'nacionalidad']

@admin.register(Pasajero)
class PasajeroAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'numero_documento', 'nacionalidad')
    search_fields = ('nombres', 'apellidos', 'numero_documento')
    list_filter = ('nacionalidad',)
    autocomplete_fields = ['nacionalidad', 'pais_emision']

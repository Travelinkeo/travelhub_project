"""Admin para Agencia."""

from django.contrib import admin
from core.models import Agencia, UsuarioAgencia


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

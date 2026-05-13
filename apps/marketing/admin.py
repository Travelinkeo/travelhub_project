from django.contrib import admin

from core.admin_saas import SaaSAdminMixin

from .models import ActivoMarketing, Campania, ConfiguracionMarketing


@admin.register(Campania)
class CampaniaAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ('nombre', 'estado', 'fecha_inicio', 'agencia')
    list_filter = ('estado', 'agencia')
    search_fields = ('nombre', 'descripcion')

@admin.register(ActivoMarketing)
class ActivoMarketingAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ('tipo', 'hotel', 'campania', 'generado_por_ia', 'fecha_creacion')
    list_filter = ('tipo', 'generado_por_ia')
    readonly_fields = ('fecha_creacion',)

@admin.register(ConfiguracionMarketing)
class ConfiguracionMarketingAdmin(SaaSAdminMixin, admin.ModelAdmin):
    list_display = ('agencia', 'color_primario', 'color_secundario')

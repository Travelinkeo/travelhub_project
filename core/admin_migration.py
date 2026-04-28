"""
Django Admin configuration for Migration Requirements Checker.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from datetime import date

from core.models import MigrationCheck
from apps.bookings.models import Venta
from core.services.migration_checker_service import MigrationCheckerService


class MigrationCheckInline(admin.TabularInline):
    """Inline para mostrar validaciones migratorias en el admin de Venta"""
    model = MigrationCheck
    extra = 0
    can_delete = False
    readonly_fields = ('alert_display', 'pasajero', 'destino', 'transit_display', 'summary', 'checked_at')
    fields = ('alert_display', 'pasajero', 'destino', 'transit_display', 'summary', 'checked_at')
    
    def alert_display(self, obj):
        """Muestra el nivel de alerta con emoji y color"""
        colors = {
            'GREEN': '#28a745',
            'YELLOW': '#ffc107',
            'RED': '#dc3545'
        }
        color = colors.get(obj.alert_level, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            obj.get_alert_emoji(),
            obj.get_alert_level_display()
        )
    alert_display.short_description = "Estado"
    
    def transit_display(self, obj):
        """Muestra los tránsitos de forma legible"""
        return obj.get_transit_display()
    transit_display.short_description = "Tránsitos"
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(MigrationCheck)
class MigrationCheckAdmin(admin.ModelAdmin):
    """Admin para gestionar validaciones migratorias"""
    list_display = ('alert_emoji_display', 'pasajero', 'destino', 'visa_status', 'passport_status', 'checked_at', 'ai_badge')
    list_filter = ('alert_level', 'visa_required', 'passport_validity_ok', 'checked_by_ai', 'checked_at')
    search_fields = ('pasajero__nombres', 'pasajero__apellidos', 'destino', 'summary')
    readonly_fields = (
        'pasajero', 'venta', 'origen', 'destino', 'transitos', 'fecha_viaje',
        'alert_level', 'visa_required', 'visa_type', 'passport_validity_ok',
        'passport_min_months_required', 'vaccination_required', 'summary',
        'full_report', 'checked_at', 'checked_by_ai', 'checked_by_user'
    )
    date_hierarchy = 'checked_at'
    
    fieldsets = (
        ('Información del Viaje', {
            'fields': ('pasajero', 'venta', 'origen', 'destino', 'transitos', 'fecha_viaje')
        }),
        ('Resultado de la Validación', {
            'fields': ('alert_level', 'summary')
        }),
        ('Requisitos de Visa', {
            'fields': ('visa_required', 'visa_type')
        }),
        ('Validez del Pasaporte', {
            'fields': ('passport_validity_ok', 'passport_min_months_required')
        }),
        ('Vacunas Requeridas', {
            'fields': ('vaccination_required',)
        }),
        ('Detalles Técnicos', {
            'fields': ('full_report', 'checked_at', 'checked_by_ai', 'checked_by_user'),
            'classes': ('collapse',)
        }),
    )
    
    def alert_emoji_display(self, obj):
        """Muestra el emoji de alerta"""
        return obj.get_alert_emoji()
    alert_emoji_display.short_description = "🚦"
    
    def visa_status(self, obj):
        """Muestra el estado de visa con formato"""
        if obj.visa_required:
            return format_html('<span style="color: #dc3545;">✗ Requiere: {}</span>', obj.visa_type)
        return format_html('<span style="color: #28a745;">✓ No requiere</span>')
    visa_status.short_description = "Visa"
    
    def passport_status(self, obj):
        """Muestra el estado del pasaporte con formato"""
        if obj.passport_validity_ok:
            return format_html('<span style="color: #28a745;">✓ Válido</span>')
        return format_html('<span style="color: #dc3545;">✗ Insuficiente</span>')
    passport_status.short_description = "Pasaporte"
    
    def ai_badge(self, obj):
        """Badge indicando si se usó IA"""
        if obj.checked_by_ai:
            return format_html('<span style="background: #007bff; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">🤖 AI</span>')
        return format_html('<span style="background: #6c757d; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">📚 DB</span>')
    ai_badge.short_description = "Fuente"
    
    def has_add_permission(self, request):
        """No permitir creación manual"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Permitir eliminación solo a superusuarios"""
        return request.user.is_superuser


# Acción para el admin de Venta
@admin.action(description='🚦 Validar Requisitos Migratorios')
def validate_migration_requirements_action(modeladmin, request, queryset):
    """
    Acción del admin para validar requisitos migratorios de ventas seleccionadas.
    """
    service = MigrationCheckerService()
    validaciones_realizadas = 0
    errores = []
    
    for venta in queryset:
        try:
            # Obtener vuelos de la venta
            segmentos = venta.segmentos_vuelo.all()
            
            if not segmentos.exists():
                errores.append(f"Venta {venta.localizador}: No tiene segmentos de vuelo")
                continue
            
            # Construir lista de vuelos
            vuelos = []
            for segmento in segmentos:
                vuelos.append({
                    'origen': segmento.origen.codigo_iata if segmento.origen else 'XXX',
                    'destino': segmento.destino.codigo_iata if segmento.destino else 'XXX',
                    'fecha': segmento.fecha_salida or date.today()
                })
            
            # Validar para cada item de venta que tenga pasajero
            items_con_pasajero = venta.items_venta.filter(pasajero__isnull=False)
            
            if not items_con_pasajero.exists():
                errores.append(f"Venta {venta.localizador}: No tiene pasajeros asignados")
                continue
            
            for item in items_con_pasajero:
                check = service.check_migration_requirements(
                    pasajero_id=item.pasajero.id_pasajero,
                    vuelos=vuelos,
                    venta_id=venta.id_venta,
                    user=request.user
                )
                validaciones_realizadas += 1
                
                # Mostrar alerta si hay problemas
                if check.alert_level in ['RED', 'YELLOW']:
                    messages.warning(
                        request,
                        f"{check.get_alert_emoji()} {item.pasajero.get_nombre_completo()}: {check.summary}"
                    )
        
        except Exception as e:
            errores.append(f"Venta {venta.localizador}: {str(e)}")
    
    if validaciones_realizadas > 0:
        messages.success(
            request,
            f"✅ Se realizaron {validaciones_realizadas} validación(es) migratoria(s)"
        )
    
    if errores:
        for error in errores[:5]:  # Mostrar máximo 5 errores
            messages.error(request, error)
        if len(errores) > 5:
            messages.warning(request, f"... y {len(errores) - 5} errores más")

import logging

from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, StackedInline

from apps.common.models import Aerolinea, Ciudad, Moneda, Pais

# Módulos admin organizados en subdirectorio core/admin/
from .admin.api_secret_admin import APISecretAdmin  # noqa: F401
from .admin_saas import SaaSAdminMixin
from .models import (
    Agencia,
    AgenciaBranding,
    AgenciaConfiguracion,
    CronApiKey,
    FeatureFlag,
    UsuarioAgencia,
)

logger = logging.getLogger(__name__)


@admin.register(Pais)
class PaisAdmin(ModelAdmin):
    """PaisAdmin."""

    list_display = ("nombre", "codigo_iso_2", "codigo_iso_3")
    search_fields = ("nombre", "codigo_iso_2", "codigo_iso_3")


@admin.register(Ciudad)
class CiudadAdmin(ModelAdmin):
    """CiudadAdmin."""

    list_display = ("nombre", "pais", "codigo_iata")
    search_fields = ("nombre", "codigo_iata", "pais__nombre")
    list_filter = ("pais",)
    autocomplete_fields = ["pais"]


@admin.register(Moneda)
class MonedaAdmin(ModelAdmin):
    """MonedaAdmin."""

    list_display = ("nombre", "codigo_iso", "simbolo", "es_moneda_local")
    search_fields = ("nombre", "codigo_iso")
    list_filter = ("es_moneda_local",)


@admin.register(Aerolinea)
class AerolineaAdmin(ModelAdmin):
    """AerolineaAdmin."""

    list_display = ("nombre", "codigo_iata", "activa")
    search_fields = ("nombre", "codigo_iata")
    list_filter = ("activa",)
    ordering = ("nombre",)


class AgenciaBrandingInline(StackedInline):
    """AgenciaBrandingInline."""

    model = AgenciaBranding
    can_delete = False
    verbose_name_plural = "Branding y Assets"


class AgenciaConfiguracionInline(StackedInline):
    """AgenciaConfiguracionInline."""

    model = AgenciaConfiguracion
    can_delete = False
    verbose_name_plural = "Configuración de Negocio y SaaS"


@admin.register(Agencia)
class AgenciaAdmin(ModelAdmin):
    """AgenciaAdmin."""

    list_display = ["nombre", "rif", "iata", "email_principal", "activa"]
    list_filter = ["activa", "pais"]
    search_fields = ["nombre", "rif", "iata"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    fieldsets = [
        (
            "Información de la Agencia",
            {
                "fields": [
                    ("nombre", "nombre_comercial"),
                    ("rif", "iata"),
                    "activa",
                    "propietario",
                ]
            },
        ),
        (
            "Contacto y Ubicación",
            {
                "fields": [
                    ("email_principal", "email_soporte", "email_ventas"),
                    ("telefono_principal", "telefono_secundario"),
                    "direccion",
                    ("ciudad", "estado", "pais", "codigo_postal"),
                ]
            },
        ),
        (
            "Redes Sociales y Web",
            {
                "classes": ("collapse",),
                "fields": [
                    "website",
                    "dominio_personalizado",
                    ("facebook", "instagram", "twitter", "whatsapp"),
                ],
            },
        ),
    ]

    def get_readonly_fields(self, request, obj=None):
        """get_readonly_fields."""
        if not request.user.is_superuser:
            return self.readonly_fields + ["rif", "iata"]
        return self.readonly_fields


@admin.register(AgenciaBranding)
class AgenciaBrandingAdmin(ModelAdmin):
    """AgenciaBrandingAdmin."""

    list_display = ["agencia_master", "ui_theme", "color_primario"]
    search_fields = ["agencia_master__nombre"]


@admin.register(AgenciaConfiguracion)
class AgenciaConfiguracionAdmin(ModelAdmin):
    """AgenciaConfiguracionAdmin."""

    list_display = ["agencia_master", "plan", "subdominio_slug", "short_keys_status"]
    search_fields = ["agencia_master__nombre", "subdominio_slug"]
    readonly_fields = [
        "ventas_mes_actual",
        "evolution_api_key_display",
        "gemini_api_key_display",
        "password_app_correo_display",
        "telegram_bot_token_display",
        "email_monitor_password_display",
        "email_monitor_last_check",
    ]

    fieldsets = [
        (
            "Plan y Límites",
            {
                "fields": [
                    ("plan", "plan_status"),
                    ("limite_mensual_boletos", "limite_usuarios", "limite_ventas_mes"),
                    "ventas_mes_actual",
                    "subscription_end_date",
                ]
            },
        ),
        (
            "Localización",
            {
                "fields": [
                    "moneda_principal",
                    "zona_horaria",
                    "idioma",
                    (
                        "imprenta_digital_nombre",
                        "imprenta_digital_rif",
                        "imprenta_digital_providencia",
                    ),
                    "es_sujeto_pasivo_especial",
                    "esta_inscrita_rtn",
                ]
            },
        ),
        (
            "WhatsApp Evolution API",
            {
                "classes": ("collapse",),
                "fields": [
                    "evolution_api_url",
                    "evolution_api_key",
                    "evolution_api_key_display",
                    "evolution_instance_name",
                ],
                "description": "Claves para integración WhatsApp multi-tenencia",
            },
        ),
        (
            "Gemini AI",
            {
                "classes": ("collapse",),
                "fields": ["gemini_api_key", "gemini_api_key_display"],
                "description": "Clave API de Gemini específica para esta agencia (opcional, si no se usa la global)",
            },
        ),
        (
            "Mailbot & Telegram",
            {
                "classes": ("collapse",),
                "fields": [
                    "correo_emisiones",
                    "password_app_correo",
                    "password_app_correo_display",
                    ("telegram_bot_token", "telegram_bot_token_display", "telegram_chat_id"),
                    "canal_notificaciones_mailbot",
                ],
            },
        ),
        (
            "Monitor IMAP",
            {
                "classes": ("collapse",),
                "fields": [
                    ("email_monitor_host", "email_monitor_port"),
                    "email_monitor_user",
                    "email_monitor_password",
                    "email_monitor_password_display",
                    "email_monitor_active",
                    "email_monitor_last_check",
                ],
            },
        ),
        (
            "Configuraciones Avanzadas (JSON)",
            {
                "classes": ("collapse",),
                "fields": ["configuracion_correo", "configuracion_api", "configuracion_contable"],
            },
        ),
    ]

    @admin.display(description="Claves")
    def short_keys_status(self, obj):
        """short_keys_status."""
        parts = []
        if obj.gemini_api_key:
            parts.append("🤖")
        if obj.evolution_api_key:
            parts.append("📱")
        if obj.telegram_bot_token:
            parts.append("✈️")
        if obj.email_monitor_password:
            parts.append("📧")
        return " ".join(parts) if parts else "—"

    @admin.display(description="API Key Evolution")
    def evolution_api_key_display(self, obj):
        """evolution_api_key_display."""
        return self._masked_field(obj.evolution_api_key)

    @admin.display(description="API Key Gemini")
    def gemini_api_key_display(self, obj):
        """gemini_api_key_display."""
        return self._masked_field(obj.gemini_api_key)

    @admin.display(description="Password App Correo")
    def password_app_correo_display(self, obj):
        """password_app_correo_display."""
        return self._masked_field(obj.password_app_correo)

    @admin.display(description="Token Telegram")
    def telegram_bot_token_display(self, obj):
        """telegram_bot_token_display."""
        return self._masked_field(obj.telegram_bot_token)

    @admin.display(description="Password IMAP")
    def email_monitor_password_display(self, obj):
        """email_monitor_password_display."""
        return self._masked_field(obj.email_monitor_password)

    def _masked_field(self, value):
        """_masked_field."""
        if not value:
            return format_html('<span style="color:#9CA3AF;">—</span>')
        visible = str(value)[:8]
        return format_html(
            '<span style="font-family:monospace;color:#6B7280;">{}</span>',
            visible + "••••",
        )

    def get_fieldsets(self, request, obj=None):
        """get_fieldsets."""
        if obj is None:
            return [(None, {"fields": ["agencia_master", "plan"]})]
        return super().get_fieldsets(request, obj)

    def has_add_permission(self, request):
        """has_add_permission."""
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """has_delete_permission."""
        return request.user.is_superuser


@admin.register(UsuarioAgencia)
class UsuarioAgenciaAdmin(ModelAdmin):
    """UsuarioAgenciaAdmin."""

    list_display = ["usuario", "agencia", "rol", "activo"]
    list_filter = ["rol", "activo", "agencia"]
    autocomplete_fields = ["usuario", "agencia"]

    def get_readonly_fields(self, request, obj=None):
        """get_readonly_fields."""
        if not request.user.is_superuser:
            return ["usuario", "agencia", "rol"]
        return []


# --- FeatureFlags ---


@admin.register(FeatureFlag)
class FeatureFlagAdmin(SaaSAdminMixin, ModelAdmin):
    """FeatureFlagAdmin."""

    list_display = ["nombre", "agencia", "enabled_badge", "rollout_percentage", "updated_at"]
    list_filter = ["enabled", "agencia"]
    search_fields = ["nombre", "description"]
    list_editable = ["rollout_percentage"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["nombre"]

    fieldsets = [
        (
            None,
            {
                "fields": [
                    "nombre",
                    "description",
                    ("enabled", "rollout_percentage"),
                    "agencia",
                ]
            },
        ),
        ("Auditoría", {"classes": ("collapse",), "fields": ("created_at", "updated_at")}),
    ]

    @admin.display(description="Activo")
    def enabled_badge(self, obj):
        """enabled_badge."""
        if obj.enabled:
            return format_html(
                '<span style="background:#D1FAE5;color:#065F46;padding:2px 8px;'
                'border-radius:4px;font-size:11px;">ON</span>'
            )
        return format_html(
            '<span style="background:#FEE2E2;color:#991B1B;padding:2px 8px;'
            'border-radius:4px;font-size:11px;">OFF</span>'
        )

    def get_queryset(self, request):
        """get_queryset."""
        return super().get_queryset(request).select_related("agencia")


# --- CronApiKeys ---


@admin.register(CronApiKey)
class CronApiKeyAdmin(SaaSAdminMixin, ModelAdmin):
    """CronApiKeyAdmin."""

    list_display = ["name", "prefix_display", "agencia", "is_active", "expires_at", "last_used"]
    list_filter = ["is_active", "agencia"]
    search_fields = ["name", "prefix"]
    readonly_fields = [
        "salt",
        "lookup_hash",
        "key_hash",
        "prefix",
        "created_at",
        "last_used",
    ]
    ordering = ["-created_at"]
    actions = ["generate_key_action"]

    fieldsets = [
        (
            None,
            {"fields": ["name", "agencia", "is_active"]},
        ),
        (
            "Clave (solo lectura)",
            {
                "fields": ["prefix", "salt", "lookup_hash", "key_hash"],
                "classes": ("collapse",),
            },
        ),
        (
            "Vigencia",
            {
                "fields": ["expires_at", "last_used"],
                "classes": ("collapse",),
            },
        ),
        ("Auditoría", {"classes": ("collapse",), "fields": ("created_at",)}),
    ]

    @admin.display(description="Prefijo")
    def prefix_display(self, obj):
        """prefix_display."""
        return format_html(
            '<code style="background:#F3F4F6;padding:2px 6px;border-radius:3px;font-size:12px;">{}</code>',
            obj.prefix,
        )

    @admin.action(description="Generar nueva clave API")
    def generate_key_action(self, request, queryset):
        """generate_key_action."""
        if queryset.count() != 1:
            self.message_user(
                request, "Selecciona exactamente 1 fila para generar una clave.", level="error"
            )
            return
        obj = queryset.first()
        new_obj, raw_key = CronApiKey.generate(name=obj.name, agencia=obj.agencia)
        self.message_user(
            request,
            f"Clave generada para '{new_obj.name}'. "
            f"COPIA AHORA: {raw_key} (no se mostrará de nuevo)",
        )

    def save_model(self, request, obj, form, change):
        """save_model."""
        if not change:
            obj, raw_key = CronApiKey.generate(name=obj.name, agencia=obj.agencia)
            obj._raw_key = raw_key
            return
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        """response_add."""
        if hasattr(obj, "_raw_key"):
            self.message_user(
                request,
                f"Clave creada. COPIA AHORA: {obj._raw_key} (no se mostrará de nuevo)",
                level="warning",
            )
        return super().response_add(request, obj, post_url_continue)

    def get_readonly_fields(self, request, obj=None):
        """get_readonly_fields."""
        if obj is None:
            return []
        return self.readonly_fields

    def get_fieldsets(self, request, obj=None):
        """get_fieldsets."""
        if obj is None:
            return [(None, {"fields": ["name", "agencia"]})]
        return super().get_fieldsets(request, obj)

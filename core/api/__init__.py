# core/api/__init__.py
# ==============================================================================
# 🏛️ PUBLIC KERNEL API
# ==============================================================================
# Este archivo centraliza la interfaz pública del núcleo del sistema (core).
# Todos los módulos de dominio (en 'apps/*') deben interactuar con las
# utilidades, managers y modelos base del core a través de esta API formal,
# en lugar de realizar importaciones directas desde sub-módulos internos.
# ==============================================================================

# --- Multi-Tenancy & Context ---
from core.cache import cache_api_response

# --- Performance & Caching ---
from core.cache_utils import (
    cache_queryset,
    invalidate_cache,
)
from core.dashboard_stats import get_dashboard_stats

# --- Central Business Events (Django Signals) ---
from core.events import (
    sale_payment_recorded,
    sale_recalculation_requested,
    ticket_invoicing_requested,
)
from core.fields import EncryptedCharField
from core.middleware import (
    agency_context,
    agency_var,
    get_current_agency,
    get_current_user,
    is_system_context,
    system_context,
)
from core.mixins import (
    AgencyRoleRequiredMixin,
    HtmxResponseMixin,
    SaaSMixin,
)

# Admin components are lazily loaded to avoid circular imports:
# core.api -> core.admin_migration -> apps.automation -> core.api
# --- Core Domain Models ---
from core.models.agencia import Agencia, AgenciaConfiguracion, UsuarioAgencia
from core.models.ai import AIUsageLog

# MigrationCheck loaded lazily below to avoid circular imports
# --- AI & Parsing Schemas ---
from core.models.ai_schemas import (
    BoletoAereoSchema,
    CedulaOCRSchema,
    InformeProveedorSchema,
    PasaporteOCRSchema,
    ResultadoParseoSchema,
    TramoVueloSchema,
)
from core.models.anulaciones import AnulacionBoleto
from core.models.api_secret import APISecret
from core.models.audit import AuditLog, crear_audit_log

# --- Base Models, Managers & Mixins ---
from core.models.base import (
    AgenciaManager,
    AgenciaMixin,
    SoftDeleteModel,
)
from core.models.magic_link import MagicLinkToken

# --- Security & Tenant helpers ---
from core.security import (
    agency_role_required,
    filter_queryset_by_tenant,
    get_agencia_from_request,
    get_agencia_or_403,
    get_object_tenant_or_404,
    get_user_active_agency,
)
from core.services.api_secrets import get_api_secret
from core.services.api_testers import test_api_secret

# --- Signal Bypass ---
from core.signals_bypass import (
    are_signals_blocked,
    disable_signals,
)

# --- Storage ---
from core.storage import RawFileStorage

# Celery tasks are loaded lazily below.
# --- Throttling ---
from core.throttling import (
    AgenciaAIParserThrottle,
    AIParserDailyQuotaThrottle,
    DashboardRateThrottle,
    LiquidacionRateThrottle,
    ReportesRateThrottle,
    UploadRateThrottle,
)

# --- Validators ---
from core.validators import (
    antivirus_hook,
    validar_no_vacio_o_espacios,
    validate_file_extension,
    validate_file_size,
)

__all__ = [
    # API Secrets
    "APISecret",
    "get_api_secret",
    "test_api_secret",
    # Context & Middleware
    "get_current_agency",
    "get_current_user",
    "agency_context",
    "system_context",
    "is_system_context",
    "agency_var",
    # Security & Tenant helpers
    "get_user_active_agency",
    "get_agencia_or_403",
    "get_agencia_from_request",
    "get_object_tenant_or_404",
    "filter_queryset_by_tenant",
    "agency_role_required",
    # Models & Mixins
    "AgenciaMixin",
    "SoftDeleteModel",
    "EncryptedCharField",
    "AgenciaManager",
    "SaaSMixin",
    "AgencyRoleRequiredMixin",
    "HtmxResponseMixin",
    "SaaSAdminMixin",
    "MigrationCheckInline",
    "validate_migration_requirements_action",
    "Agencia",
    "UsuarioAgencia",
    "AgenciaConfiguracion",
    "AuditLog",
    "crear_audit_log",
    "AnulacionBoleto",
    "MagicLinkToken",
    "AIUsageLog",
    "ResultadoParseoSchema",
    "CedulaOCRSchema",
    "PasaporteOCRSchema",
    "BoletoAereoSchema",
    "TramoVueloSchema",
    "InformeProveedorSchema",
    # Events / Signals
    "sale_payment_recorded",
    "sale_recalculation_requested",
    "ticket_invoicing_requested",
    # Validators
    "validar_no_vacio_o_espacios",
    "antivirus_hook",
    "validate_file_extension",
    "validate_file_size",
    # Storage
    "RawFileStorage",
    # Cache
    "cache_queryset",
    "invalidate_cache",
    "cache_api_response",
    "get_dashboard_stats",
    # Celery Tasks
    "parsear_boleto_individual",
    "procesar_facturacion_masiva_task",
    "procesar_correo_individual_agencia",
    "enviar_notificacion_whatsapp_task",
    # Serializers
    "CoreClienteSerializer",
    "MonedaSerializer",
    # Throttling
    "AgenciaAIParserThrottle",
    "AIParserDailyQuotaThrottle",
    "DashboardRateThrottle",
    "LiquidacionRateThrottle",
    "ReportesRateThrottle",
    "UploadRateThrottle",
    # Signal Bypass
    "are_signals_blocked",
    "disable_signals",
]


_LAZY_ADMIN_ATTRS = {
    # Admin components (cause circular imports via core.admin_migration -> apps.automation -> core.api)
    "SaaSAdminMixin": "core.admin_saas.SaaSAdminMixin",
    "MigrationCheckInline": "core.admin_migration.MigrationCheckInline",
    "validate_migration_requirements_action": "core.admin_migration.validate_migration_requirements_action",
    # Models
    "MigrationCheck": "core.models.migration_checks.MigrationCheck",
    # Serializers (avoid circular imports at startup)
    "CoreClienteSerializer": "core.serializers.CoreClienteSerializer",
    "MonedaSerializer": "core.serializers.MonedaSerializer",
    # Celery tasks (lazy load to avoid circular imports during app population)
    "parsear_boleto_individual": "core.tasks.parsear_boleto_individual",
    "procesar_facturacion_masiva_task": "core.tasks.procesar_facturacion_masiva_task",
    "procesar_correo_individual_agencia": "core.tasks.procesar_correo_individual_agencia",
    "enviar_notificacion_whatsapp_task": "core.tasks.enviar_notificacion_whatsapp_task",
}


def __getattr__(name: str):
    if name in _LAZY_ADMIN_ATTRS:
        from django.utils.module_loading import import_string

        return import_string(_LAZY_ADMIN_ATTRS[name])
    raise AttributeError(f"module 'core.api' has no attribute {name!r}")

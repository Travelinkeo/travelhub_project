"""
travelhub/settings/base.py
==========================
Configuración base compartida por todos los entornos (dev, prod, test).
NO contiene secretos ni flags específicos de entorno.

Para usar un entorno específico:
  DJANGO_SETTINGS_MODULE=travelhub.settings.production
  DJANGO_SETTINGS_MODULE=travelhub.settings.development
  DJANGO_SETTINGS_MODULE=travelhub.settings.testing
"""

import json
import logging
import mimetypes
import os
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import dj_database_url
import environ
from django.utils.translation import gettext_lazy as _

from core.utils.redis_utils import build_redis_url

# Importar la configuración de Unfold admin (tema visual)
from ..settings_unfold import UNFOLD  # noqa: F401

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class ZoneInfoEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles ZoneInfo serialization."""

    def default(self, obj):
        """default."""
        if isinstance(obj, ZoneInfo):
            return str(obj)
        return super().default(obj)


JSON_ENCODER_CLASS = "travelhub.settings.base.ZoneInfoEncoder"

# Fix para registro de mimetypes en Windows local (evita bloqueo "nosniff" de scripts CSS/JS)
mimetypes.add_type("text/css", ".css", True)
mimetypes.add_type("application/javascript", ".js", True)
mimetypes.add_type("application/javascript", ".mjs", True)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rutas base
# ---------------------------------------------------------------------------

# settings/ → travelhub/ → proyecto/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Variables de entorno
# ---------------------------------------------------------------------------

env = environ.Env(
    DEBUG=(bool, False),
    USE_R2=(bool, True),
    ALLOWED_HOSTS=(list, ["127.0.0.1", "localhost"]),
    SENTRY_DSN=(str, ""),
    GEMINI_API_KEY=(str, ""),
    STRIPE_SECRET_KEY=(str, ""),
)

# Carga de variables de entorno con prioridad:
#   1. .env.local  → desarrollo local (secretos reales, sobreescribe todo)
#   2. .env        → fallback (Docker Compose + valores placeholder para Django)
_env_local = BASE_DIR / ".env.local"
_env_base = BASE_DIR / ".env"

if _env_local.exists():
    environ.Env.read_env(_env_local)
    logger.info("🔑 Entorno cargado desde: .env.local")
elif _env_base.exists():
    environ.Env.read_env(_env_base)
    logger.info("🔑 Entorno cargado desde: .env (fallback base)")
else:
    logger.warning(
        "⚠️ No se encontró ningún archivo .env ni .env.local. "
        "Las variables de entorno deben estar inyectadas por el sistema (Docker, CI/CD)."
    )

# ---------------------------------------------------------------------------
# Core settings
# ---------------------------------------------------------------------------

DEBUG = env("DEBUG")
USE_R2 = env("USE_R2")
SECRET_KEY = env("SECRET_KEY")
SENTRY_DSN = env("SENTRY_DSN")

GEMINI_API_KEY = env("GEMINI_API_KEY")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY")

DATABASE_URL = env("DATABASE_URL")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

MAIN_DOMAIN = env("MAIN_DOMAIN", default="travelhub.cc")
SITE_DOMAIN = env("SITE_DOMAIN", default="travelhub.cc")
EMAIL_DOMAIN = env("EMAIL_DOMAIN", default="travelhub.cc")

# ---------------------------------------------------------------------------
# Auth & Login
# ---------------------------------------------------------------------------

LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"
LOGIN_URL = "login"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# ---------------------------------------------------------------------------
# Installed Apps
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.humanize",
    "django.contrib.postgres",
    "django.contrib.staticfiles",
    "mathfilters",
    "storages",
    # Apps de Terceros
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "drf_spectacular",
    "django_filters",
    "django_prometheus",
    "waffle",
    # TravelHub Apps (Orden Crítico)
    "apps.common.apps.CommonConfig",
    "core.apps.CoreConfig",  # Módulo Núcleo (SaaS/Arqui/Auth)
    "apps.bookings.apps.BookingsConfig",  # Nuevo Módulo Bookings
    "apps.finance.apps.FinanceConfig",  # Nuevo Módulo Finance
    "apps.cotizaciones.apps.CotizacionesConfig",  # App para Cotizaciones
    "apps.contabilidad.apps.ContabilidadConfig",
    "apps.marketing.apps.MarketingConfig",
    "apps.cms.apps.CmsConfig",
    "apps.crm.apps.CrmConfig",
    "apps.gamification.apps.GamificationConfig",
    "apps.reports.apps.ReportsConfig",
    "apps.tasks.apps.TasksConfig",
    "apps.communications.apps.CommunicationsConfig",
    "apps.automation.apps.AutomationConfig",
    "django_celery_results",
    "django_celery_beat",
    "axes",
    "django_extensions",
]

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Servir estáticos
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # i18n: detección de idioma
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "core.middleware_onboarding.OnboardingRedirectMiddleware",
    "core.middleware.MultiTenantDomainMiddleware",
    "core.middleware.ThreadLocalContextMiddleware",
    "core.middleware.SecurityHeadersMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware_saas.SaaSLimitMiddleware",
    "core.middleware_ai_ratelimit.AIRateLimitMiddleware",
    "core.middleware_performance.QueryCountDebugMiddleware",
    "core.middleware_performance.CacheHeaderMiddleware",
    "waffle.middleware.WaffleMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

# ---------------------------------------------------------------------------
# Templates, URLs, WSGI
# ---------------------------------------------------------------------------

ROOT_URLCONF = "travelhub.urls"
WSGI_APPLICATION = "travelhub.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "core" / "templates"],  # Priorizar templates de core (overrides)
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.agency_context",
                "core.context_processors.csp_nonce",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Databases
# ---------------------------------------------------------------------------

DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}

# 🛡️ P1-003: Si se usa PgBouncer en pool_mode = transaction, CONN_MAX_AGE debe ser 0
# para evitar que variables RLS de sesión (SET LOCAL) se fuguen al reutilizar conexiones.
USE_PGBOUNCER = env.bool("USE_PGBOUNCER", default=False)
conn_max_age_val = 0 if USE_PGBOUNCER else 600

DATABASES["default"]["CONN_MAX_AGE"] = conn_max_age_val
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

# ═══════════════════════════════════════════════════════════════════════════════
# 🛡️ PARCHE CRÍTICO RLS: ATOMIC_REQUESTS
# ═══════════════════════════════════════════════════════════════════════════════
# Envuelve CADA request en una transacción. El SET LOCAL app.current_agencia_id
# hecho por ThreadLocalContextMiddleware queda ACOPLADO a la vida de esta
# transacción. Al finalizar (commit/rollback), Postgres purga automáticamente
# TODAS las variables locales de sesión. Esto elimina la fuga de RLS si un
# worker colapsa antes del bloque finally del middleware.
#
# ⚠️ ATOMIC_REQUESTS = True  tiene costo: una transacción extra por request.
# Para endpoints de solo lectura pública (health, landing, status), añadir
# la anotación @transaction.non_atomic_requests al view correspondiente.
# ═══════════════════════════════════════════════════════════════════════════════
DATABASES["default"]["ATOMIC_REQUESTS"] = True

# --- READ REPLICA (opcional) ---
# Configurar DATABASE_REPLICA_URL en el entorno para activar la réplica.
_replica_url = env("DATABASE_REPLICA_URL", default=DATABASE_URL)
DATABASES["replica"] = dj_database_url.parse(_replica_url)
DATABASES["replica"]["CONN_MAX_AGE"] = conn_max_age_val
DATABASES["replica"]["CONN_HEALTH_CHECKS"] = True
DATABASES["replica"]["DISABLE_SERVER_SIDE_CURSORS"] = True
DATABASES["replica"]["TEST"] = {"MIRROR": "default"}

if _replica_url != DATABASE_URL:
    DATABASE_ROUTERS = ["core.db_router.PrimaryReplicaRouter"]

# ---------------------------------------------------------------------------
# Password Validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internacionalización (i18n)
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Caracas"
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ("es", _("Español")),
    ("en", _("English")),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# ---------------------------------------------------------------------------
# Static & Media files
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_ROOT = BASE_DIR / "media"

# Límites de upload (20MB para logos PNG de alta resolución)
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

# ---------------------------------------------------------------------------
# Cloudflare R2 / Storage
# ---------------------------------------------------------------------------

AWS_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
AWS_S3_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
AWS_S3_REGION_NAME = "auto"
AWS_S3_CUSTOM_DOMAIN = os.getenv("AWS_S3_CUSTOM_DOMAIN")
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None

if USE_R2:
    _r2_storage_opts = {
        "default_acl": "private",
    }
    if AWS_S3_CUSTOM_DOMAIN:
        _r2_storage_opts["custom_domain"] = AWS_S3_CUSTOM_DOMAIN
        _r2_storage_opts["querystring_auth"] = False
    else:
        _r2_storage_opts["querystring_auth"] = True
        _r2_storage_opts["querystring_expire"] = 60 * 60 * 24 * 7  # 7 días

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": _r2_storage_opts,
        },
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
    }
    MEDIA_URL = (
        f"https://{AWS_S3_CUSTOM_DOMAIN}/"
        if AWS_S3_CUSTOM_DOMAIN
        else f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/"
    )
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
    }
    MEDIA_URL = "/media/"

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
FIXTURE_DIRS = [BASE_DIR / "fixtures"]

WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_MANIFEST_STRICT = False

# ---------------------------------------------------------------------------
# Third-party API keys
# ---------------------------------------------------------------------------

UNSPLASH_ACCESS_KEY = env("UNSPLASH_ACCESS_KEY", default="")
UNSPLASH_SECRET_KEY = env("UNSPLASH_SECRET_KEY", default="")

STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_IDS = {
    "BASIC": os.getenv("STRIPE_PRICE_ID_BASIC", ""),
    "PRO": os.getenv("STRIPE_PRICE_ID_PRO", ""),
    "ENTERPRISE": os.getenv("STRIPE_PRICE_ID_ENTERPRISE", ""),
}

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")
TELEGRAM_GROUP_ID = os.getenv("TELEGRAM_GROUP_ID")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")
TELEGRAM_STORAGE_CHANNEL_ID = os.getenv("TELEGRAM_STORAGE_CHANNEL_ID", "-1003225870613")
TELEGRAM_FINANZAS_CHAT_ID = os.getenv("TELEGRAM_FINANZAS_CHAT_ID", "")

WHATSAPP_MICROSERVICE_URL = os.getenv("WHATSAPP_MICROSERVICE_URL", "http://evolution:8080")
WHATSAPP_MICROSERVICE_TOKEN = os.getenv("WHATSAPP_MICROSERVICE_TOKEN")
EVOLUTION_PUBLIC_URL = os.getenv("EVOLUTION_PUBLIC_URL", "http://localhost:8080")
EVOLUTION_INSTANCE_TOKEN = os.getenv("EVOLUTION_INSTANCE_TOKEN")
EVOLUTION_WEBHOOK_URL = os.getenv("EVOLUTION_WEBHOOK_URL", "http://web:8000/crm/webhook/evolution/")
WHATSAPP_NOTIFICATIONS_ENABLED = (
    os.getenv("WHATSAPP_NOTIFICATIONS_ENABLED", "true").lower() == "true"
)
WHATSAPP_APP_SECRET = env("WHATSAPP_APP_SECRET", default="")
WHATSAPP_VERIFY_TOKEN = env("WHATSAPP_VERIFY_TOKEN", default="")
WHATSAPP_TOKEN = env("WHATSAPP_TOKEN", default="")
WHATSAPP_PHONE_ID = env("WHATSAPP_PHONE_ID", default="")
TWILIO_WHATSAPP_NUMBER = env("TWILIO_WHATSAPP_NUMBER", default="")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", default="")

# Endpoint interno donde el monitor proactivo puede llamar al health-check
# del flujo WhatsApp/Evolution. Por defecto localhost si Django y Celery
# corren en el mismo contenedor (web). En setups con Django separado,
# configurar DJANGO_BASE_URL=http://web:8000 o similar.
DJANGO_BASE_URL = os.getenv("DJANGO_BASE_URL", "http://localhost:8000")

# Token opcional para autenticar requests del monitor worker al health-check
# (no es auth, solo previene que cualquiera pueda triggerear load innecesario).
# Si está vacío, el monitor hace requests sin autenticación extra.
MONITOR_SERVICE_TOKEN = os.getenv("MONITOR_SERVICE_TOKEN", "")

BINANCE_PAY_API_KEY = env("BINANCE_PAY_API_KEY", default="")
BINANCE_PAY_SECRET_KEY = env("BINANCE_PAY_SECRET_KEY", default="")
BINANCE_WEBHOOK_SECRET = env("BINANCE_WEBHOOK_SECRET", default="")

GOOGLE_PLACES_API_KEY = env(
    "GOOGLE_PLACES_API_KEY", default=os.environ.get("GOOGLE_PLACES_API_KEY", "")
)

MAGIC_LINK_BASE_URL = os.getenv("MAGIC_LINK_BASE_URL", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", MAGIC_LINK_BASE_URL or "http://localhost:8000")
LIVE_CHAT_ID = os.getenv("LIVE_CHAT_ID", "")

# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework.authentication.TokenAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "50/minute",
        "user": "200/minute",
        "dashboard": "100/hour",
        "liquidacion": "50/hour",
        "reportes": "20/hour",
        "upload": "30/hour",
        "ai_parser_quota": "20/minute",
        "ai_parser_daily": "200/day",
    },
}

# ---------------------------------------------------------------------------
# OpenAPI / Spectacular
# ---------------------------------------------------------------------------

SPECTACULAR_SETTINGS = {
    "TITLE": "TravelHub API",
    "DESCRIPTION": (
        "API REST de TravelHub — CRM/ERP SaaS para Agencias de Viajes.\n\n"
        "**Características:**\n"
        "- Gestión de Boletos Aéreos (KIU, SABRE, AMADEUS)\n"
        "- Facturación VEN-NIF (IVA, IGTF, doble moneda)\n"
        "- Contabilidad automatizada (Plan de Cuentas, Asientos)\n"
        "- CRM con Kanban IA y gestión de clientes\n"
        "- Conciliación inteligente y liquidación a proveedores\n"
        "- Dashboard de métricas y alertas en tiempo real\n"
        "- Multi-tenancy (SaaS con planes FREE/BASIC/PRO/ENTERPRISE)\n\n"
        "Autenticación vía JWT, Token o Session según el endpoint."
    ),
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_AUTHENTICATION": None,
    "COMPONENT_SPLIT_PATCH": True,
    "COMPONENT_SPLIT_CREATABLE": True,
    "ENUM_ADD_EXPLICIT_BLANK": False,
    "SCHEMA_PATH_PREFIX": r"/api/",
    "SCHEMA_PATH_PREFIX_TRIM": True,
    "TAGS": [
        {"name": "Autenticación", "description": "Login JWT, Magic Links, Logout"},
        {"name": "Dashboard", "description": "Métricas, alertas y KPIs del dashboard"},
        {"name": "Boletos", "description": "Gestión de boletos aéreos importados"},
        {"name": "Ventas", "description": "Operaciones CRUD de ventas, reservas y facturación"},
        {"name": "Facturación", "description": "Facturas consolidadas VEN-NIF"},
        {"name": "Contabilidad", "description": "Plan de cuentas, asientos contables, reportes"},
        {"name": "Liquidaciones", "description": "Liquidación a proveedores y pagos"},
        {"name": "CRM", "description": "Clientes, pasaportes, oportunidades Kanban"},
        {"name": "Auditoría", "description": "Traza de auditoría y logs del sistema"},
        {"name": "Tasas BCV", "description": "Tasas de cambio oficiales de Venezuela"},
        {
            "name": "Catálogos",
            "description": "Catálogos base: países, ciudades, monedas, aerolíneas",
        },
        {"name": "Admin", "description": "Endpoints administrativos y de configuración SaaS"},
        {"name": "Cron", "description": "Tareas programadas internas (cron-job.org)"},
    ],
    "SERVERS": [
        {"url": "https://travelhub.cc", "description": "Producción"},
        {"url": "http://localhost:8000", "description": "Desarrollo local"},
    ],
    "CONTACT": {
        "name": "TravelHub Team",
        "email": "soporte@travelhub.cc",
        "url": "https://travelhub.cc",
    },
    "LICENSE": {"name": "Proprietary — TravelHub SaaS", "url": "https://travelhub.cc/terms"},
    "SECURITY": [{"BearerAuth": []}, {"TokenAuth": []}, {"SessionAuth": []}],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Token JWT obtenido via POST /api/auth/jwt/obtain/",
            },
            "TokenAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
                "description": "Token de API en formato: Token <valor>",
            },
            "SessionAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "sessionid",
                "description": "Cookie de sesión Django",
            },
        },
    },
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
        "defaultModelsExpandDepth": 1,
        "defaultModelExpandDepth": 1,
        "docExpansion": "list",
        "filter": True,
        "showExtensions": True,
        "syntaxHighlight": {"theme": "monokai"},
    },
}

# ---------------------------------------------------------------------------
# SaaS Plans
# ---------------------------------------------------------------------------

SAAS_PLAN_LIMITS = {
    "FREE": {"users": 1, "storage_mb": 100, "leads_per_month": 20, "sales_per_month": 20},
    "BASIC": {"users": 2, "storage_mb": 500, "leads_per_month": 50, "sales_per_month": 50},
    "PRO": {"users": 10, "storage_mb": 5000, "leads_per_month": 500, "sales_per_month": 500},
    "ENTERPRISE": {
        "users": 999,
        "storage_mb": 99999,
        "leads_per_month": 99999,
        "sales_per_month": 99999,
    },
}

# ---------------------------------------------------------------------------
# Email (base: console en dev, SMTP en prod)
# ---------------------------------------------------------------------------

_resend_key = os.getenv("RESEND_API_KEY", "")

if _resend_key:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    RESEND_API_KEY = _resend_key
    RESEND_SIGNING_SECRET = os.environ.get("RESEND_SIGNING_SECRET", "")
    EMAIL_HOST = "smtp.resend.com"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = "resend"
    EMAIL_HOST_PASSWORD = _resend_key
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "TravelHub <noreply@travelhub.cc>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
SITE_URL = os.getenv("SITE_URL", "https://travelhub.cc")
DEMO_NOTIFY_EMAIL = os.getenv("DEMO_NOTIFY_EMAIL", "ventas@travelhub.app")

# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------

_redis_url_env = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL")
_default_redis_host = _default_redis_password = _default_redis_port = None
if _redis_url_env:
    try:
        from urllib.parse import urlparse

        _parsed = urlparse(_redis_url_env)
        if _parsed.hostname:
            _default_redis_host = _parsed.hostname
        if _parsed.port:
            _default_redis_port = str(_parsed.port)
        if _parsed.password:
            _default_redis_password = _parsed.password
    except Exception:
        logger.debug("No se pudo parsear REDIS_URL; usando defaults de entorno")

_raw_redis_pass = (
    os.getenv("REDIS_CACHE_PASSWORD")
    or _default_redis_password
    or os.getenv("REDIS_PASSWORD")
    or "ROTATE_BEFORE_PROD_REDIS_PASSWORD"
)
if _raw_redis_pass and _raw_redis_pass.endswith("_DEV"):
    _raw_redis_pass = _raw_redis_pass[:-4]

_redis_cache_password = _raw_redis_pass
_redis_cache_host = os.getenv("REDIS_CACHE_HOST", _default_redis_host or "redis_cache")
_redis_cache_port = os.getenv("REDIS_CACHE_PORT", _default_redis_port or "6379")

_redis_celery_password = _raw_redis_pass
_redis_celery_host = os.getenv("REDIS_CELERY_HOST", _default_redis_host or "redis_broker")
_redis_celery_port = os.getenv("REDIS_CELERY_PORT", _default_redis_port or "6379")

_redis_evolution_password = _raw_redis_pass
_redis_evolution_host = os.getenv("REDIS_EVOLUTION_HOST", _default_redis_host or "redis_evolution")
_redis_evolution_port = os.getenv("REDIS_EVOLUTION_PORT", _default_redis_port or "6379")


# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------

CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    build_redis_url(_redis_celery_host, _redis_celery_port, _redis_celery_password, 0),
)
CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    build_redis_url(_redis_celery_host, _redis_celery_port, _redis_celery_password, 0),
)
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_RESULT_EXPIRES = 3600
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 500

CELERY_TASK_ROUTES = {
    # ── Cola notifications (WhatsApp, Telegram, Email) ──────────────
    "apps.common.tasks.send_whatsapp_task": {"queue": "notifications"},
    "apps.common.tasks.send_telegram_task": {"queue": "notifications"},
    "apps.common.tasks.send_email_task": {"queue": "notifications"},
    "apps.common.tasks.enviar_notificacion_whatsapp_task": {"queue": "notifications"},
    "apps.bookings.tasks.notificar_pago_whatsapp_task": {"queue": "notifications"},
    "apps.automation.tasks.send_ticket_notification": {"queue": "notifications"},
    "apps.common.tasks.send_whatsapp_meta_task": {"queue": "notifications"},
    "apps.common.tasks.send_evolution_message_task": {"queue": "notifications"},
    "apps.common.tasks.send_evolution_document_task": {"queue": "notifications"},
    "apps.common.tasks.send_factura_to_telegram_task": {"queue": "notifications"},
    "apps.common.tasks.send_telegram_document_task": {"queue": "notifications"},
    "apps.common.tasks.send_telegram_photo_task": {"queue": "notifications"},
    # ── Cola celery (todo lo demás: IA, batch, parsing) ────────────
    # No se necesita entrada explícita porque "celery" es la cola default.
    # apps.automation.tasks.process_web_uploaded_ticket → ia_fast removido, va a default
}

try:
    from ..celery_beat_schedule import CELERY_BEAT_SCHEDULE  # noqa: F401
except ImportError:
    logger.warning("⚠️ celery_beat_schedule.py no encontrado — las tareas cron no se ejecutarán.")
    CELERY_BEAT_SCHEDULE = {}

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_cache_url = os.getenv(
    "REDIS_CACHE_URL",
    build_redis_url(_redis_cache_host, _redis_cache_port, _redis_cache_password, 0),
)
_session_url = os.getenv(
    "REDIS_SESSIONS_URL",
    build_redis_url(_redis_cache_host, _redis_cache_port, _redis_cache_password, 1),
)

if "redis://" in _cache_url:
    _cache_options = {
        "CLIENT_CLASS": "django_redis.client.DefaultClient",
        "CONNECTION_POOL_KWARGS": {"max_connections": 50},
    }
    if _redis_cache_password and "@" not in _cache_url:
        _cache_options["PASSWORD"] = _redis_cache_password

    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": _cache_url,
            "OPTIONS": _cache_options,
            "KEY_PREFIX": "th",
            "TIMEOUT": 300,
        },
        "sessions": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": _session_url,
            "OPTIONS": _cache_options,
            "KEY_PREFIX": "th_sess",
            "TIMEOUT": 3600,
        },
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
    SESSION_CACHE_ALIAS = "sessions"
    SESSION_SAVE_EVERY_REQUEST = False
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

# ---------------------------------------------------------------------------
# CORS & CSRF
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000",
    ).split(",")
]
CORS_ALLOW_CREDENTIALS = True

_env_csrf_origins = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "https://travelhub.cc,http://travelhub.cc,http://localhost:8000,http://127.0.0.1:8000",
)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _env_csrf_origins.split(",")]

# ---------------------------------------------------------------------------
# Security (base — overridden per environment)
# ---------------------------------------------------------------------------

ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
ENCRYPTION_SALT = os.environ.get("ENCRYPTION_SALT", None)

# django-axes: Protección contra fuerza bruta
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]
AXES_RESET_ON_SUCCESS = True
AXES_ENABLE_ACCESS_FAILURE_LOG = True
AXES_HANDLER = "axes.handlers.cache.AxesCacheHandler"
AXES_CACHE = "default"

SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
# SECURE_PROXY_SSL_HEADER se define solo en producción (production.py):
# debe estar activo ÚNICAMENTE cuando hay un reverse proxy (Traefik/Cloudflare)
# que garantiza X-Forwarded-Proto. Definirlo en base/dev sin proxy permite
# spoofing del esquema (un atacante puede inyectar X-Forwarded-Proto: https
# para byass validaciones SSL). Por seguridad fall-closed, en base queda None.
SECURE_PROXY_SSL_HEADER = None
SECURE_REDIRECT_EXEMPT = [r"^health/$", r"^health$"]

# JWT
# Usar JWT_SIGNING_KEY separada de SECRET_KEY para limitar el impacto
# si SECRET_KEY se ve comprometida (SECRET_KEY también firma sesiones, CSRF, etc.)
_JWT_SIGNING_KEY = env("JWT_SIGNING_KEY", default=SECRET_KEY)
if _JWT_SIGNING_KEY == SECRET_KEY:
    logging.getLogger("settings").warning(
        "⚠️ JWT_SIGNING_KEY NO configurada — se está usando SECRET_KEY. "
        "Configura JWT_SIGNING_KEY en .env (requerido en producción)."
    )
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": _JWT_SIGNING_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
}

# Cookies
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # HTMX/JS necesita leer el CSRF token
SESSION_COOKIE_AGE = 14400  # 4 horas
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_NAME = "th_csrftoken"
SESSION_COOKIE_NAME = "th_sessionid"

# System check silencing
SILENCED_SYSTEM_CHECKS = [
    "urls.W005",
    "fields.W342",
]

# ---------------------------------------------------------------------------
# Logging estructurado (importado desde settings_logging.py)
# ---------------------------------------------------------------------------

try:
    from ..settings_logging import *  # noqa: F403, F405
except ImportError:
    pass

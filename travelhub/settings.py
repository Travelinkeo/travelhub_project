import json
import logging
import mimetypes
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import dj_database_url
import sentry_sdk
from django.core.exceptions import ImproperlyConfigured
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration


class ZoneInfoEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles ZoneInfo serialization."""

    def default(self, obj):
        if isinstance(obj, ZoneInfo):
            return str(obj)
        return super().default(obj)


JSON_ENCODER_CLASS = f"{__name__}.ZoneInfoEncoder"

# Fix para registro de mimetypes en Windows local (evita bloqueo "nosniff" de scripts CSS/JS)
mimetypes.add_type("text/css", ".css", True)
mimetypes.add_type("application/javascript", ".js", True)
mimetypes.add_type("application/javascript", ".mjs", True)

# Configurar un logger básico para mensajes en settings
logger = logging.getLogger(__name__)

LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"
LOGIN_URL = "login"


import environ  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent

# Instanciar el entorno de variables con django-environ (tipado y casteado estricto)
env = environ.Env(
    DEBUG=(bool, False),
    USE_R2=(bool, True),
    ALLOWED_HOSTS=(list, ["127.0.0.1", "localhost"]),
    SENTRY_DSN=(str, ""),
    GEMINI_API_KEY=(str, ""),
    STRIPE_SECRET_KEY=(str, ""),
)

# Carga el archivo .env si existe (útil en dev; en prod se inyectan en el SO o Docker)
environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env("DEBUG")
USE_R2 = env("USE_R2")

# --- VARIABLES CRÍTICAS (STRICT MODE) ---
# django-environ arrojará ImproperlyConfigured automáticamente si SECRET_KEY o DATABASE_URL no están.
SECRET_KEY = env("SECRET_KEY")

GEMINI_API_KEY = env("GEMINI_API_KEY")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY")

# Validación en producción — falla rápido si falta alguna variable
if not DEBUG and len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("🔒 SECRET_KEY debe tener al menos 50 caracteres en producción")

DATABASE_URL = env("DATABASE_URL")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")


# Configuracion de Sentry
SENTRY_DSN = env("SENTRY_DSN")
if SENTRY_DSN.startswith("http"):
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=0.1,
        profiles_sample_rate=0.01,
    )
# print("--- [SETTINGS] Apps defined ---", flush=True)

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
    "apps.communications.apps.CommunicationsConfig",
    "apps.automation.apps.AutomationConfig",
    "django_celery_results",
    "django_celery_beat",
    "axes",
    # 'django_extensions',
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Servir estáticos en Render
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
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

# --- WHITENOISE CONFIG (CRÍTICO PARA DOCKER + DEBUG) ---
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_MANIFEST_STRICT = False

ROOT_URLCONF = "travelhub.urls"

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

WSGI_APPLICATION = "travelhub.wsgi.application"


DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}
DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

# print("--- [SETTINGS] DB configured ---", flush=True)

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "es-ve"
TIME_ZONE = "America/Caracas"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# --- UNIFIED STORAGE STRATEGY (CLOUDFLARE R2) ---
# Cloudflare R2 is our single source of truth for media files ($0 egress fees)
AWS_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
AWS_S3_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
AWS_S3_REGION_NAME = "auto"
AWS_S3_CUSTOM_DOMAIN = os.getenv("AWS_S3_CUSTOM_DOMAIN")
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None  # R2 handles permissions at bucket level, ACLs are not supported

if USE_R2:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
    MEDIA_URL = (
        f"https://{AWS_S3_CUSTOM_DOMAIN}/"
        if AWS_S3_CUSTOM_DOMAIN
        else f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/"
    )
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }
    MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"

# --- LÍMITES DE UPLOAD ---
# 20MB para soportar logos PNG de alta resolución
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20 MB

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

FIXTURE_DIRS = [
    BASE_DIR / "fixtures",
]
# print("--- [SETTINGS] Fixtures configured ---", flush=True)

# Gemini API Key (ya definida arriba como GEMINI_API_KEY)

# Marketing - Unsplash API
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
UNSPLASH_SECRET_KEY = os.getenv("UNSPLASH_SECRET_KEY")

# --- STRIPE BILLING & SAAS ---
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

STRIPE_PRICE_IDS = {
    "BASIC": os.getenv("STRIPE_PRICE_ID_BASIC", ""),
    "PRO": os.getenv("STRIPE_PRICE_ID_PRO", ""),
    "ENTERPRISE": os.getenv("STRIPE_PRICE_ID_ENTERPRISE", ""),
}

# Configuración REST Framework
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

# SPECTACULAR SETTINGS — OpenAPI 3.0 Documentation
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
    "SERVE_AUTHENTICATION": None,  # Swagger UI auth handled manually
    "COMPONENT_SPLIT_PATCH": True,
    "COMPONENT_SPLIT_CREATABLE": True,
    "ENUM_ADD_EXPLICIT_BLANK": False,
    "SCHEMA_PATH_PREFIX": r"/api/",
    "SCHEMA_PATH_PREFIX_TRIM": True,
    # 🏷️ Tags organizados por módulo funcional
    "TAGS": [
        {"name": "Autenticación", "description": "Login JWT, Magic Links, Logout"},
        {"name": "Dashboard", "description": "Métricas, alertas y KPIs del dashboard"},
        {
            "name": "Boletos",
            "description": "Gestión de boletos aéreos importados (upload, parseo, búsqueda)",
        },
        {"name": "Ventas", "description": "Operaciones CRUD de ventas, reservas y facturación"},
        {"name": "Facturación", "description": "Facturas consolidadas VEN-NIF, doble facturación"},
        {"name": "Contabilidad", "description": "Plan de cuentas, asientos contables, reportes"},
        {"name": "Liquidaciones", "description": "Liquidación a proveedores y pagos"},
        {"name": "CRM", "description": "Clientes, pasaportes, oportunidades Kanban"},
        {"name": "Auditoría", "description": "Traza de auditoría y logs del sistema"},
        {
            "name": "Tasas BCV",
            "description": "Tasas de cambio oficiales de Venezuela (BCV, Paralelo, P2P)",
        },
        {
            "name": "Catálogos",
            "description": "Catálogos base: países, ciudades, monedas, aerolíneas",
        },
        {"name": "Admin", "description": "Endpoints administrativos y de configuración SaaS"},
        {"name": "Cron", "description": "Tareas programadas internas (cron-job.org)"},
    ],
    # 🌐 Servidores de la API
    "SERVERS": [
        {"url": "https://travelhub.cc", "description": "Producción"},
        {"url": "http://localhost:8000", "description": "Desarrollo local"},
    ],
    # 🔐 Contacto del equipo
    "CONTACT": {
        "name": "TravelHub Team",
        "email": "soporte@travelhub.cc",
        "url": "https://travelhub.cc",
    },
    # 📄 Licencia
    "LICENSE": {
        "name": "Proprietary — TravelHub SaaS",
        "url": "https://travelhub.cc/terms",
    },
    # 🛡️ Seguridad: Esquemas de autenticación globales
    "SECURITY": [
        {"BearerAuth": []},
        {"TokenAuth": []},
        {"SessionAuth": []},
    ],
    # 🔐 Definición de esquemas de seguridad
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
                "description": "Cookie de sesión Django (autenticación vía login)",
            },
        },
    },
    # 📝 Extensiones para mejor documentación
    "EXTENSIONS": {
        "x-business-model": "SaaS Multi-Tenant Travel Agency ERP",
        "x-tech-stack": "Django 5.x + HTMX + Alpine.js + PostgreSQL + Redis",
    },
    # ⚙️ Swagger UI customization
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

# --- SaaS & Limits ---
SAAS_PLAN_LIMITS = {
    "FREE": {
        "users": 1,
        "storage_mb": 100,
        "leads_per_month": 20,
        "sales_per_month": 20,
    },
    "BASIC": {
        "users": 2,
        "storage_mb": 500,
        "leads_per_month": 50,
        "sales_per_month": 50,
    },
    "PRO": {
        "users": 10,
        "storage_mb": 5000,
        "leads_per_month": 500,
        "sales_per_month": 500,
    },
    "ENTERPRISE": {
        "users": 999,
        "storage_mb": 99999,
        "leads_per_month": 99999,
        "sales_per_month": 99999,
    },
}

# ✉️ EMAIL — Resend SMTP
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
    logger.info("📧 Email Engine: RESEND Activado")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    logger.info("📧 Email Engine: CONSOLE (Desarrollo)")

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "TravelHub <noreply@travelhub.cc>")

SERVER_EMAIL = DEFAULT_FROM_EMAIL


# Redes Sociales y Notificaciones
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")
TELEGRAM_GROUP_ID = os.getenv("TELEGRAM_GROUP_ID")

# 📱 WhatsApp Microservice (Evolution API v2)
WHATSAPP_MICROSERVICE_URL = os.getenv("WHATSAPP_MICROSERVICE_URL", "http://evolution:8080")
WHATSAPP_MICROSERVICE_TOKEN = os.getenv("WHATSAPP_MICROSERVICE_TOKEN")
if not DEBUG and not WHATSAPP_MICROSERVICE_TOKEN:
    raise ImproperlyConfigured("WHATSAPP_MICROSERVICE_TOKEN debe configurarse en producción")
EVOLUTION_PUBLIC_URL = os.getenv("EVOLUTION_PUBLIC_URL", "http://localhost:8080")
EVOLUTION_INSTANCE_TOKEN = os.getenv("EVOLUTION_INSTANCE_TOKEN")
if not DEBUG and not EVOLUTION_INSTANCE_TOKEN:
    raise ImproperlyConfigured("EVOLUTION_INSTANCE_TOKEN debe configurarse en producción")

# 🔐 Binance Pay API (creación de órdenes y webhooks)
BINANCE_PAY_API_KEY = os.getenv("BINANCE_PAY_API_KEY")
BINANCE_PAY_SECRET_KEY = os.getenv("BINANCE_PAY_SECRET_KEY")
if not DEBUG and not BINANCE_PAY_API_KEY:
    raise ImproperlyConfigured("BINANCE_PAY_API_KEY debe configurarse en producción")
BINANCE_WEBHOOK_SECRET = os.getenv("BINANCE_WEBHOOK_SECRET", "")

# PDF Generation (Gotenberg)
GOTENBERG_URL = os.getenv("GOTENBERG_URL", "")

# GCP - Document AI
GCP_JSON_CREDENTIALS = os.getenv("GCP_JSON_CREDENTIALS")

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION = os.getenv("GCP_LOCATION")

# --- REDIS CONFIGURATION ---
# Centralized Redis configuration with password support
_redis_password = os.getenv("REDIS_PASSWORD", None)
_redis_host = os.getenv("REDIS_HOST", "redis")
_redis_port = os.getenv("REDIS_PORT", "6379")


def _build_redis_url(db_num=0):
    """Build Redis URL with optional password authentication."""
    if _redis_password:
        return f"redis://:{_redis_password}@{_redis_host}:{_redis_port}/{db_num}"
    return f"redis://{_redis_host}:{_redis_port}/{db_num}"


# Celery Configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", _build_redis_url(0))
CELERY_BEAT_SCHEDULE = {}

CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", _build_redis_url(0))
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_RESULT_EXPIRES = 3600
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 500

# --- CELERY BEAT SCHEDULE ---

# --- CACHE CONFIGURATION ---
# ☁️ Redis Cache: Compartido con Celery para entornos distribuídos (Gunicorn workers)
_cache_url = _build_redis_url(1)
_session_url = _build_redis_url(2)

if "redis://" in _cache_url:
    cache_options = {
        "CLIENT_CLASS": "django_redis.client.DefaultClient",
        "CONNECTION_POOL_KWARGS": {"max_connections": 50},
    }
    # Agregar autenticación si está configurada
    if _redis_password:
        cache_options["PASSWORD"] = _redis_password

    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": _cache_url,
            "OPTIONS": cache_options,
            "KEY_PREFIX": "th",
            "TIMEOUT": 300,
        },
        "sessions": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": _session_url,
            "OPTIONS": cache_options,
            "KEY_PREFIX": "th_sess",
            "TIMEOUT": 3600,  # 1 hora
        },
    }

    # 🔑 Redis Sessions: Backend de sesiones con Redis para escalabilidad
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "sessions"
    SESSION_SAVE_EVERY_REQUEST = False
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,https://travelhub-fe.vercel.app",
    ).split(",")
]
CORS_ALLOW_CREDENTIALS = True

# Dominios confiables para CSRF (Obligatorio en producción o detrás de proxy inverso como Cloudflare)
# Se pueden cargar múltiples dominios en .env separados por comas (Ej: https://erp.travelhub.cc,https://miagencia.com)
env_csrf_origins = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "https://travelhub.cc,http://travelhub.cc,http://localhost:8000,http://127.0.0.1:8000",
)
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in env_csrf_origins.split(",")]

# -----------------------------------------------------
# 🔒 PADLOCK: SECURITY INFRASTRUCTURE
# PROTECCION DE DATOS PERSONALES (GDPR/Compliance)
# -----------------------------------------------------

ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
if not DEBUG and not ENCRYPTION_KEY:
    raise ImproperlyConfigured("ENCRYPTION_KEY debe configurarse en producción")
if not DEBUG and ENCRYPTION_KEY and len(ENCRYPTION_KEY) < 32:
    raise ImproperlyConfigured("ENCRYPTION_KEY debe tener al menos 32 caracteres")

ENCRYPTION_SALT = os.environ.get("ENCRYPTION_SALT", None)

# --- django-axes: Proteccion contra fuerza bruta ---
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # horas de bloqueo tras exceder el limite
AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]
AXES_RESET_ON_SUCCESS = True
AXES_ENABLE_ACCESS_FAILURE_LOG = True

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# CSP Report-only para testing (luego poner en producción)
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# --- Magic Link Auth ---
MAGIC_LINK_BASE_URL = os.getenv("MAGIC_LINK_BASE_URL", "")  # Auto-detect from request if empty
FRONTEND_URL = os.getenv("FRONTEND_URL", MAGIC_LINK_BASE_URL or "http://localhost:8000")

# --- JWT Config (si se usa) ---
# ... (opcional)

# -----------------------------------------------------
# 🐒 MONKEY PATCHES & CONFIGURACIONES FINALES
# -----------------------------------------------------

# Arreglo para WeasyPrint (si se usa para PDFs)
# ...

# 🏎️ FIN DE CONFIGURACIÓN

# --- UNFOLD CONFIGURATION ---
UNFOLD = {
    "SITE_TITLE": "TravelHub Admin",
    "SITE_SYMBOL": "travel_explore",
    "STYLES": [
        "/static/css/custom_admin.css",
    ],
    "COLORS": {
        "primary": {
            "50": "239 246 255",
            "100": "219 234 254",
            "200": "191 219 254",
            "300": "147 197 253",
            "400": "96 165 250",
            "500": "59 130 246",
            "600": "37 99 235",
            "700": "29 78 216",
            "800": "30 64 175",
            "900": "30 58 138",
            "950": "23 37 84",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Operaciones",
                "collapsible": True,
                "items": [
                    {"title": "Dashboard Principal", "icon": "dashboard", "link": "/dashboard/"},
                    {
                        "title": "Subir Boleto (IA)",
                        "icon": "upload_file",
                        "link": "/erp/boletos-importar/",
                    },
                    {
                        "title": "Buffer de Revision",
                        "icon": "rate_review",
                        "link": "/erp/boletos-importados/",
                    },
                ],
            },
            {
                "title": "Ventas y Reservas",
                "collapsible": True,
                "items": [
                    {"title": "Ventas", "icon": "shopping_cart", "link": "/admin/bookings/venta/"},
                    {
                        "title": "Items de Venta",
                        "icon": "list_alt",
                        "link": "/admin/bookings/itemventa/",
                    },
                    {
                        "title": "Boletos Importados",
                        "icon": "flight",
                        "link": "/admin/bookings/boletoimportado/",
                    },
                    {
                        "title": "Segmentos de Vuelo",
                        "icon": "connecting_airports",
                        "link": "/admin/bookings/segmentovuelo/",
                    },
                    {
                        "title": "Alojamientos",
                        "icon": "hotel",
                        "link": "/admin/bookings/alojamientoreserva/",
                    },
                    {
                        "title": "Traslados",
                        "icon": "airport_shuttle",
                        "link": "/admin/bookings/trasladoservicio/",
                    },
                    {
                        "title": "Actividades",
                        "icon": "hiking",
                        "link": "/admin/bookings/actividadservicio/",
                    },
                    {
                        "title": "Alquiler de Autos",
                        "icon": "directions_car",
                        "link": "/admin/bookings/alquileroautoreserva/",
                    },
                    {
                        "title": "Circuitos",
                        "icon": "map",
                        "link": "/admin/bookings/circuitoturistico/",
                    },
                    {
                        "title": "Paquetes Aereos",
                        "icon": "flight_takeoff",
                        "link": "/admin/bookings/paquetesereo/",
                    },
                    {
                        "title": "Cruceros",
                        "icon": "directions_boat",
                        "link": "/admin/bookings/cruceroreserva/",
                    },
                    {
                        "title": "Fee de Venta",
                        "icon": "attach_money",
                        "link": "/admin/bookings/feeventa/",
                    },
                    {
                        "title": "Pagos de Venta",
                        "icon": "payments",
                        "link": "/admin/bookings/pagoventa/",
                    },
                    {
                        "title": "Proveedores",
                        "icon": "local_shipping",
                        "link": "/admin/bookings/proveedor/",
                    },
                    {
                        "title": "Productos y Servicios",
                        "icon": "inventory",
                        "link": "/admin/bookings/productoservicio/",
                    },
                ],
            },
            {
                "title": "Hoteles y Tarifarios",
                "collapsible": True,
                "items": [
                    {
                        "title": "Tarifarios Proveedor",
                        "icon": "request_quote",
                        "link": "/admin/bookings/tarifarioproveedor/",
                    },
                    {
                        "title": "Hoteles en Tarifario",
                        "icon": "king_bed",
                        "link": "/admin/bookings/hoteltarifario/",
                    },
                    {
                        "title": "Tipos de Habitacion",
                        "icon": "bed",
                        "link": "/admin/bookings/tipohabitacion/",
                    },
                    {
                        "title": "Tarifas por Temporada",
                        "icon": "calendar_month",
                        "link": "/admin/bookings/tarifahabitacion/",
                    },
                    {"title": "Amenities", "icon": "spa", "link": "/admin/bookings/amenity/"},
                ],
            },
            {
                "title": "CRM",
                "collapsible": True,
                "items": [
                    {"title": "Clientes", "icon": "people", "link": "/admin/crm/cliente/"},
                    {"title": "Pasajeros", "icon": "person", "link": "/admin/crm/pasajero/"},
                    {
                        "title": "Oportunidades (Kanban)",
                        "icon": "lightbulb",
                        "link": "/admin/crm/oportunidadviaje/",
                    },
                    {
                        "title": "Pasaportes Escaneados",
                        "icon": "scanner",
                        "link": "/admin/crm/pasaporteescaneado/",
                    },
                ],
            },
            {
                "title": "Cotizaciones",
                "collapsible": True,
                "items": [
                    {
                        "title": "Cotizaciones",
                        "icon": "description",
                        "link": "/admin/cotizaciones/cotizacion/",
                    },
                    {
                        "title": "Items Cotizacion",
                        "icon": "format_list_bulleted",
                        "link": "/admin/cotizaciones/itemcotizacion/",
                    },
                ],
            },
            {
                "title": "Finanzas",
                "collapsible": True,
                "items": [
                    {
                        "title": "Facturas",
                        "icon": "receipt_long",
                        "link": "/admin/finance/factura/",
                    },
                    {
                        "title": "Facturas Consolidadas",
                        "icon": "description",
                        "link": "/admin/finance/facturaconsolidada/",
                    },
                    {"title": "Libro de Ventas", "icon": "menu_book", "link": "/api/libro-ventas/"},
                    {
                        "title": "Gastos Operativos",
                        "icon": "money_off",
                        "link": "/admin/finance/gastooperativo/",
                    },
                    {
                        "title": "Pagos (Link de Pago)",
                        "icon": "link",
                        "link": "/admin/finance/linkdepago/",
                    },
                    {
                        "title": "Conciliaciones",
                        "icon": "compare_arrows",
                        "link": "/admin/finance/conciliacionboleto/",
                    },
                    {
                        "title": "Retenciones ISLR",
                        "icon": "receipt",
                        "link": "/admin/finance/retencionislr/",
                    },
                ],
            },
            {
                "title": "Contabilidad",
                "collapsible": True,
                "items": [
                    {
                        "title": "Plan de Cuentas",
                        "icon": "account_tree",
                        "link": "/admin/contabilidad/plancontable/",
                    },
                    {
                        "title": "Asientos Contables",
                        "icon": "book",
                        "link": "/admin/contabilidad/asientocontable/",
                    },
                    {
                        "title": "Tasas BCV",
                        "icon": "currency_exchange",
                        "link": "/admin/contabilidad/tasacambiobcv/",
                    },
                    {"title": "Reportes Contables", "icon": "assessment", "link": "/reportes/"},
                ],
            },
            {
                "title": "Marketing",
                "collapsible": True,
                "items": [
                    {"title": "Campañas", "icon": "campaign", "link": "/admin/marketing/campania/"},
                    {
                        "title": "Activos Marketing",
                        "icon": "photo_library",
                        "link": "/admin/marketing/activomarketing/",
                    },
                    {
                        "title": "Config Marketing",
                        "icon": "settings",
                        "link": "/admin/marketing/configuracionmarketing/",
                    },
                    {
                        "title": "Centro de Marketing",
                        "icon": "auto_awesome",
                        "link": "/marketing/hub/",
                    },
                ],
            },
            {
                "title": "CMS / Contenido",
                "collapsible": True,
                "items": [
                    {"title": "Articulos", "icon": "article", "link": "/admin/cms/articulo/"},
                    {
                        "title": "Guias de Destino",
                        "icon": "travel_explore",
                        "link": "/admin/cms/guiadestino/",
                    },
                    {
                        "title": "Posts Redes",
                        "icon": "share",
                        "link": "/admin/cms/postredessociales/",
                    },
                ],
            },
            {
                "title": "Configuracion Global",
                "collapsible": True,
                "items": [
                    {"title": "Agencias", "icon": "corporate_fare", "link": "/admin/core/agencia/"},
                    {"title": "Usuarios", "icon": "group", "link": "/admin/auth/user/"},
                    {"title": "Paises", "icon": "public", "link": "/admin/common/pais/"},
                    {"title": "Ciudades", "icon": "location_city", "link": "/admin/common/ciudad/"},
                    {"title": "Aerolineas", "icon": "flight", "link": "/admin/common/aerolinea/"},
                    {"title": "Monedas", "icon": "paid", "link": "/admin/finance/moneda/"},
                    {
                        "title": "Tipos de Cambio",
                        "icon": "trending_up",
                        "link": "/admin/finance/tipocambio/",
                    },
                    {
                        "title": "Feature Flags",
                        "icon": "toggle_on",
                        "link": "/admin/core/featureflag/",
                    },
                    {"title": "Cron API Keys", "icon": "key", "link": "/admin/core/cronapikey/"},
                    {"title": "Audit Logs", "icon": "history", "link": "/admin/core/auditlog/"},
                ],
            },
            {
                "title": "SuperAdmin",
                "collapsible": True,
                "items": [
                    {"title": "Control de Mando", "icon": "shield", "link": "/system/god-mode/"},
                    {
                        "title": "Gestion de Agencias",
                        "icon": "corporate_fare",
                        "link": "/admin/core/agencia/",
                    },
                    {
                        "title": "IA - GDS Analyzer",
                        "icon": "analytics",
                        "link": "/system/intelligence/gds-analyzer/",
                    },
                    {
                        "title": "Conciliacion Proveedores",
                        "icon": "account_balance",
                        "link": "/finance/supplier-reconciliation/",
                    },
                ],
            },
            {
                "title": "Ajustes de Agencia",
                "collapsible": True,
                "items": [
                    {
                        "title": "Configuración de Agencias",
                        "icon": "corporate_fare",
                        "link": "/admin/core/agencia/",
                    },
                    {
                        "title": "Branding y Logos",
                        "icon": "palette",
                        "link": "/admin/core/agenciabranding/",
                    },
                    {
                        "title": "Parámetros SaaS",
                        "icon": "settings",
                        "link": "/admin/core/agenciaconfiguracion/",
                    },
                    {
                        "title": "Usuarios de Agencia",
                        "icon": "group",
                        "link": "/admin/core/usuarioagencia/",
                    },
                ],
            },
        ],
    },
}
# print("--- [SETTINGS] Loaded successfully ---", flush=True)

# Cargar configuracion de logging estructurado
try:
    from .settings_logging import *  # noqa: F403, F405
except ImportError:
    pass

# -----------------------------------------------------
# 🔒 BLOQUE DE SEGURIDAD HTTP/HTTPS
# Todas estas flags se activan SOLO en producción (DEBUG=False).
# En desarrollo local (DEBUG=True) permanecen en False para evitar
# romper el servidor HTTP local.
# -----------------------------------------------------
# El header que Nginx/Cloudflare usa para indicar que la conexión original era HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    SECURE_SSL_REDIRECT = True

    # HSTS: Decirle al browser que SOLO use HTTPS por 1 año
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Cookies seguras (solo se envían por HTTPS)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Protección contra clickjacking
    X_FRAME_OPTIONS = "DENY"

    # Prevenir que el browser "olfatee" el tipo de contenido
    SECURE_CONTENT_TYPE_NOSNIFF = True
else:
    # En desarrollo, cookies sin HTTPS para no romper el servidor local
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False
    X_FRAME_OPTIONS = "SAMEORIGIN"

# Siempre activos independiente del modo:
SESSION_COOKIE_HTTPONLY = True  # JS no puede leer la cookie de sesión
CSRF_COOKIE_HTTPONLY = False  # HTMX/JS necesita leer el CSRF token
SESSION_COOKIE_AGE = 14400  # 4 horas
CSRF_COOKIE_NAME = "th_csrftoken"
SESSION_COOKIE_NAME = "th_sessionid"


is_testing = os.environ.get("DJANGO_TESTING", "False") == "True"

if is_testing:
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    # Desactivar R2 en tests para evitar delays de red
    STORAGES["default"] = {"BACKEND": "django.core.files.storage.FileSystemStorage"}
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

import os
import ssl
import logging
from datetime import timedelta
from pathlib import Path
import mimetypes

# Fix para registro de mimetypes en Windows local (evita bloqueo "nosniff" de scripts CSS/JS)
mimetypes.add_type("text/css", ".css", True)
mimetypes.add_type("application/javascript", ".js", True)
mimetypes.add_type("application/javascript", ".mjs", True)

# Configurar un logger básico para mensajes en settings
logger = logging.getLogger(__name__)

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
print("--- [SETTINGS] .env loaded ---", flush=True)

# DEBUG defaults to False for safety. Set DEBUG=True in .env for development.
DEBUG = os.getenv('DEBUG', 'False') == 'True'

from django.core.exceptions import ImproperlyConfigured

# 🛑 ESCUDO DE SEGURIDAD (FAIL FAST)
# Si falta alguna de estas variables en producción, el servidor se negará a arrancar.
def get_env_variable(var_name, default=None, required=True):
    try:
        return os.environ[var_name]
    except KeyError:
        if required and not DEBUG:
            error_msg = f"🔥 FALLO CRÍTICO DE SEGURIDAD: Falta la variable de entorno obligatoria '{var_name}'"
            raise ImproperlyConfigured(error_msg)
        return default

# --- VARIABLES CRÍTICAS ---
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-for-local-only')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')

# Validación en producción — falla rápido si falta alguna variable
if not DEBUG:
    if SECRET_KEY == 'django-insecure-dev-key-for-local-only':
        raise ImproperlyConfigured("SECRET_KEY debe configurarse con un valor seguro en producción")
    if len(SECRET_KEY) < 50:
        raise ImproperlyConfigured("SECRET_KEY debe tener al menos 50 caracteres")
    if not GEMINI_API_KEY:
        import logging; logging.getLogger('travelhub').warning("GEMINI_API_KEY no definida — funcionalidades de IA deshabilitadas")
    if not STRIPE_SECRET_KEY:
        import logging; logging.getLogger('travelhub').warning("STRIPE_SECRET_KEY no definida — funcionalidades de pago deshabilitadas")

try:
    DATABASE_URL = os.environ['DATABASE_URL']
except KeyError:
    raise ImproperlyConfigured("🔥 FALLO CRÍTICO DE ARQUITECTURA: DATABASE_URL para PostgreSQL es obligatoria y no está definida.")

# Solo permitimos el dominio en producción
ALLOWED_HOSTS = get_env_variable('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')


# Configuracion de Sentry
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN and not DEBUG:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.2,
        send_default_pii=False,
        environment=os.getenv('SENTRY_ENVIRONMENT', 'production'),
    )
print("--- [SETTINGS] Apps defined ---", flush=True)

INSTALLED_APPS = [
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'mathfilters',
    'storages',
    
    # Apps de Terceros
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'drf_spectacular',
    'django_filters',
    
    # TravelHub Apps (Orden Crítico)
    'apps.common.apps.CommonConfig',
    'core.apps.CoreConfig', # Módulo Núcleo (SaaS/Arqui/Auth)
    'apps.bookings.apps.BookingsConfig', # Nuevo Módulo Bookings
    'apps.finance.apps.FinanceConfig', # Nuevo Módulo Finance
    'apps.cotizaciones.apps.CotizacionesConfig', # App para Cotizaciones
    'apps.contabilidad.apps.ContabilidadConfig',
    'apps.marketing.apps.MarketingConfig',
    'apps.cms.apps.CmsConfig',
    'apps.crm.apps.CrmConfig',
    'apps.communications.apps.CommunicationsConfig',
    'apps.automation.apps.AutomationConfig',
    'django_celery_results',
    'django_celery_beat',
    # 'django_extensions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Servir estáticos en Render
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.ThreadLocalContextMiddleware',
    'core.middleware.SecurityHeadersMiddleware',
     'django.contrib.messages.middleware.MessageMiddleware',
     'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware_saas.SaaSLimitMiddleware',
    'core.middleware_ai_ratelimit.AIRateLimitMiddleware',
]

ROOT_URLCONF = 'travelhub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'core' / 'templates'], # Priorizar templates de core (overrides)
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.agency_context',
                'core.context_processors.csp_nonce',
            ],
        },
    },
]

WSGI_APPLICATION = 'travelhub.wsgi.application'

# Base de datos: PostgreSQL guiado estrictamente por DATABASE_URL
import dj_database_url
DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL)
}
# Connection pooling para alta concurrencia
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['CONN_HEALTH_CHECKS'] = True
print("--- [SETTINGS] DB configured ---", flush=True)

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

LANGUAGE_CODE = 'es-ve'
TIME_ZONE = 'America/Caracas'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Cloudinary Strategy (PDFs & Media)
# Configurado de forma perezosa
import cloudinary

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
}

# Configurar cloudinary directamente
if CLOUDINARY_STORAGE.get('CLOUD_NAME'):
    cloudinary.config(
        cloud_name=CLOUDINARY_STORAGE['CLOUD_NAME'],
        api_key=CLOUDINARY_STORAGE['API_KEY'],
        api_secret=CLOUDINARY_STORAGE['API_SECRET'],
        secure=True
    )
    # Configurar opciones por defecto para uploads
    CLOUDINARY_STORAGE['OPTIONS'] = {
        'resource_type': 'raw',
        'access_mode': 'public',  # PDFs públicos por defecto
        'type': 'upload'
    }
print("--- [SETTINGS] Cloudinary configured ---", flush=True)

# Media files - Usar Cloudinary en desarrollo y producción
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'  # Siempre definir MEDIA_ROOT
# --- ESTRATEGIA DE ALMACENAMIENTO (HÍBRIDA) ---
USE_CLOUDINARY = os.getenv('USE_CLOUDINARY', 'False') == 'True'
USE_R2 = os.getenv('USE_R2', 'False') == 'True'

if USE_R2:
    # ☁️ CLOUDFLARE R2 (S3 Compatible) - RECOMENDADO POR RENDIMIENTO Y COSTO $0 EGRESS
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "access_key": os.getenv("R2_ACCESS_KEY_ID"),
                "secret_key": os.getenv("R2_SECRET_ACCESS_KEY"),
                "bucket_name": os.getenv("R2_BUCKET_NAME"),
                "endpoint_url": os.getenv("R2_ENDPOINT_URL"),
                "region_name": "auto",
                "custom_domain": None,  # Por ahora usamos el endpoint directo
                "file_overwrite": False, # Evitar sobreescribir archivos con el mismo nombre
            },
        },
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
    }
    logger.info(f"🚀 Cloudflare R2 Activado (Bucket: {os.getenv('R2_BUCKET_NAME')})")
elif USE_CLOUDINARY:
    # ☁️ CLOUDINARY FALLBACK
    STORAGES = {
        "default": {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
    }
else:
    # 💻 DISCO LOCAL (DESARROLLO)
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

FIXTURE_DIRS = [BASE_DIR / 'fixtures',]
print("--- [SETTINGS] Fixtures configured ---", flush=True)

# Gemini API Key
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Marketing - Unsplash API
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')
UNSPLASH_SECRET_KEY = os.getenv('UNSPLASH_SECRET_KEY')

# --- STRIPE BILLING & SAAS ---
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

STRIPE_PRICE_IDS = {
    'BASIC': os.getenv('STRIPE_PRICE_ID_BASIC', ''),
    'PRO': os.getenv('STRIPE_PRICE_ID_PRO', ''),
    'ENTERPRISE': os.getenv('STRIPE_PRICE_ID_ENTERPRISE', ''),
}

# Configuración REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'dashboard': '100/hour',
        'liquidacion': '50/hour',
        'reportes': '20/hour',
        'upload': '30/hour',
        'ai_parser_quota': '20/minute',
        'ai_parser_daily': '200/day',
    }
}

# SPECTACULAR SETTINGS
SPECTACULAR_SETTINGS = {
    'TITLE': 'TravelHub API',
    'DESCRIPTION': 'Documentación de API para TravelHub GDS e Inteligencia Turística',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_PATCH': True,
    'COMPONENT_SPLIT_CREATABLE': True,
}

# --- SaaS & Limits ---
SAAS_PLAN_LIMITS = {
    'FREE': {
        'users': 1,
        'storage_mb': 100,
        'leads_per_month': 20,
        'sales_per_month': 20,
    },
    'BASIC': {
        'users': 2,
        'storage_mb': 500,
        'leads_per_month': 50,
        'sales_per_month': 50,
    },
    'PRO': {
        'users': 10,
        'storage_mb': 5000,
        'leads_per_month': 500,
        'sales_per_month': 500,
    },
    'ENTERPRISE': {
        'users': 999,
        'storage_mb': 99999,
        'leads_per_month': 99999,
        'sales_per_month': 99999,
    }
}

# ✉️ EMAIL — SendGrid SMTP
# SendGrid expone SMTP en smtp.sendgrid.net:587.
# El username SIEMPRE es la cadena literal 'apikey'.
# La password es tu SENDGRID_API_KEY del .env.
# Fallback a consola en local si la clave no está configurada.
# ✉️ ESTRATEGIA DE EMAIL (RESEND > SENDGRID > CONSOLE)
_resend_key = os.getenv('RESEND_API_KEY', '')
_sendgrid_key = os.getenv('SENDGRID_API_KEY', '')

if _resend_key:
    # 🚀 MODO RESEND (Primario) - Usando django-resend si está disponible o directo
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend' # O un backend específico
    RESEND_API_KEY = _resend_key
    RESEND_SIGNING_SECRET = os.environ.get('RESEND_SIGNING_SECRET', '')
    # Configuración SMTP de Resend (Alternativa rápida y compatible)
    EMAIL_HOST = 'smtp.resend.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = 'resend'
    EMAIL_HOST_PASSWORD = _resend_key
    logger.info("📧 Email Engine: RESEND (SMTP) Activado")

elif _sendgrid_key and not _sendgrid_key.startswith('SG.pon-'):
    # 🥈 MODO SENDGRID (Fallback)
    EMAIL_BACKEND  = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST     = 'smtp.sendgrid.net'
    EMAIL_PORT     = 587
    EMAIL_USE_TLS  = True
    EMAIL_HOST_USER     = 'apikey'
    EMAIL_HOST_PASSWORD = _sendgrid_key
    logger.info("📧 Email Engine: SENDGRID Activado")

else:
    # 💻 MODO DESARROLLO (Consola)
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    logger.info("📧 Email Engine: CONSOLE (Desarrollo)")

DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'TravelHub <noreply@travelhub.cc>')

SERVER_EMAIL = DEFAULT_FROM_EMAIL


# Redes Sociales y Notificaciones
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_ADMIN_ID = os.getenv('TELEGRAM_ADMIN_ID')
TELEGRAM_GROUP_ID = os.getenv('TELEGRAM_GROUP_ID')

# 📱 WhatsApp Microservice (Evolution API / VPS)
WHATSAPP_MICROSERVICE_URL = os.getenv('WHATSAPP_MICROSERVICE_URL', 'http://localhost:3000/send')
WHATSAPP_MICROSERVICE_TOKEN = os.getenv('WHATSAPP_MICROSERVICE_TOKEN')

# GCP - Document AI
GCP_JSON_CREDENTIALS = os.getenv('GCP_JSON_CREDENTIALS') 

# Celery Configuration (Disabled for debug)
# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# --- CELERY BEAT SCHEDULE ---
from travelhub.celery_beat_schedule import CELERY_BEAT_SCHEDULE

# --- CACHE CONFIGURATION ---
# ☁️ Redis Cache: Compartido con Celery para entornos distribuídos (Gunicorn workers)
# Usamos la misma URL que Celery pero en la DB 1 para separar del broker
_redis_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
_cache_url = _redis_url.replace('/0', '/1') # Usamos DB 1

if 'redis://' in _cache_url:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": _cache_url,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {"max_connections": 50}
            },
            "KEY_PREFIX": "th",
            "TIMEOUT": 300,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "https://travelhub-fe.vercel.app",
]
CORS_ALLOW_CREDENTIALS = True

# Dominios confiables para CSRF (Obligatorio en producción o detrás de proxy inverso como Cloudflare)
# Se pueden cargar múltiples dominios en .env separados por comas (Ej: https://erp.travelhub.cc,https://miagencia.com)
env_csrf_origins = os.getenv('CSRF_TRUSTED_ORIGINS', 'https://travelhub.cc,http://travelhub.cc')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in env_csrf_origins.split(',')]

import logging
logger = logging.getLogger(__name__)

# -----------------------------------------------------
# 🔒 PADLOCK: SECURITY INFRASTRUCTURE
# PROTECCION DE DATOS PERSONALES (GDPR/Compliance)
# -----------------------------------------------------

ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', '')
if not DEBUG and not ENCRYPTION_KEY:
    raise ImproperlyConfigured("ENCRYPTION_KEY debe configurarse en producción")
if not DEBUG and ENCRYPTION_KEY and len(ENCRYPTION_KEY) < 32:
    raise ImproperlyConfigured("ENCRYPTION_KEY debe tener al menos 32 caracteres")

# 🛰️ CONFIGURACIÓN DE SEGURIDAD (HSTS / CSP)
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
X_FRAME_OPTIONS = 'DENY'

# CSP Report-only para testing (luego poner en producción)
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# --- Magic Link Auth ---
MAGIC_LINK_BASE_URL = os.getenv('MAGIC_LINK_BASE_URL', '')  # Auto-detect from request if empty

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
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Operaciones",
                "items": [
                    {
                        "title": "Dashboard Principal",
                        "icon": "dashboard",
                        "link": "/dashboard/",
                    },
                    {
                        "title": "Subir Boleto (IA)",
                        "icon": "upload_file",
                        "link": "/erp/boletos-importar/",
                    },
                    {
                        "title": "Buffer de Revisión",
                        "icon": "rate_review",
                        "link": "/erp/boletos-importados/",
                    },
                ],
            },
            {
                "title": "SuperAdmin (God Mode)",
                "items": [
                    {
                        "title": "Control de Mando",
                        "icon": "shield",
                        "link": "/god-mode/",
                    },
                    {
                        "title": "Gestión de Agencias",
                        "icon": "corporate_fare",
                        "link": "/admin/core/agencia/",
                    },
                ],
            },
            {
                "title": "Marketing & IA",
                "items": [
                    {
                        "title": "Centro de Marketing",
                        "icon": "auto_awesome",
                        "link": "/marketing/hub/",
                    },
                    {
                        "title": "Analizador GDS",
                        "icon": "analytics",
                        "link": "/intelligence/gds-analyzer/",
                    },
                ],
            },
            {
                "title": "Finanzas y Contabilidad",
                "items": [
                    {
                        "title": "Facturación",
                        "icon": "receipt_long",
                        "link": "/facturacion/",
                    },
                    {
                        "title": "Facturas Consolidadas",
                        "icon": "description",
                        "link": "/api/facturas-consolidadas/",
                    },
                    {
                        "title": "Libro de Ventas",
                        "icon": "menu_book",
                        "link": "/api/libro-ventas/",
                    },
                    {
                        "title": "Reportes Contables",
                        "icon": "assessment",
                        "link": "/reportes/",
                    },
                    {
                        "title": "Conciliación Proveedores",
                        "icon": "account_balance",
                        "link": "/finance/supplier-reconciliation/",
                    },
                ],
            },
            {
                "title": "Configuración",
                "items": [
                    {
                        "title": "Perfil de Usuario",
                        "icon": "manage_accounts",
                        "link": "/setup/perfil/",
                    },
                    {
                        "title": "Branding",
                        "icon": "palette",
                        "link": "/settings/branding/",
                    },
                    {
                        "title": "Configuración Agencia",
                        "icon": "settings",
                        "link": "/agencia/configuracion/",
                    },
                    {
                        "title": "Catálogos",
                        "icon": "inventory_2",
                        "link": "/setup/catalogos/",
                    },
                    {
                        "title": "Gestión de Usuarios",
                        "icon": "group",
                        "link": "/agencia/usuarios/",
                    },
                    {
                        "title": "Tasas de Cambio",
                        "icon": "currency_exchange",
                        "link": "/setup/tasas/",
                    },
                ],
            },
        ],
    },
}
print("--- [SETTINGS] Loaded successfully ---", flush=True)

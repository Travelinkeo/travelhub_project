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
# En desarrollo (DEBUG=True) usará los defaults. En Producción exigirá las variables reales.
SECRET_KEY = get_env_variable('SECRET_KEY', 'django-insecure-dev-key', required=True)
GEMINI_API_KEY = get_env_variable('GEMINI_API_KEY', 'gemini-dev-key', required=True)
STRIPE_SECRET_KEY = get_env_variable('STRIPE_SECRET_KEY', 'sk_test_dev', required=True)

try:
    DATABASE_URL = os.environ['DATABASE_URL']
except KeyError:
    raise ImproperlyConfigured("🔥 FALLO CRÍTICO DE ARQUITECTURA: DATABASE_URL para PostgreSQL es obligatoria y no está definida.")

# Solo permitimos el dominio en producción
ALLOWED_HOSTS = get_env_variable('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')


# Configuración de Sentry (Desactivado temporalmente para evitar hangs)
# import sentry_sdk
# from sentry_sdk.integrations.django import DjangoIntegration
# 
# SENTRY_DSN = os.getenv('SENTRY_DSN')
# if SENTRY_DSN:
#     sentry_sdk.init(
#         dsn=SENTRY_DSN,
#         integrations=[DjangoIntegration()],
#         traces_sample_rate=1.0,
#         send_default_pii=True
#     )

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
    'core.apps.CoreConfig', # Módulo Núcleo (SaaS/Arqui/Auth)
    'apps.bookings.apps.BookingsConfig', # Nuevo Módulo Bookings
    'apps.finance.apps.FinanceConfig', # Nuevo Módulo Finance
    'apps.cotizaciones.apps.CotizacionesConfig', # App para Cotizaciones
    'apps.contabilidad.apps.ContabilidadConfig',
    'apps.marketing.apps.MarketingConfig',
    'apps.cms.apps.CmsConfig',
    'apps.crm.apps.CrmConfig',
    'apps.accounting_assistant.apps.AccountingAssistantConfig',
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
    'core.middleware.ThreadLocalContextMiddleware',  # captura contexto (User/Agency/IP) en thread-local
    'core.middleware.SecurityHeadersMiddleware',  # security headers & CSP report-only
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware_saas.SaaSLimitMiddleware',  # Verificar límites de plan SaaS
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
    'default': dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

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
    'BASIC': {
        'users': 2,
        'storage_mb': 500,
        'leads_per_month': 50,
        'sales_per_month': 50,
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
_sendgrid_key = os.getenv('SENDGRID_API_KEY', '')

if _sendgrid_key and not _sendgrid_key.startswith('SG.pon-'):
    # 🚀 MODO REAL — SendGrid SMTP (transaccional, sin riesgo de bloqueo de Gmail)
    EMAIL_BACKEND  = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST     = 'smtp.sendgrid.net'
    EMAIL_PORT     = 587
    EMAIL_USE_TLS  = True
    EMAIL_HOST_USER     = 'apikey'         # literal requerido por SendGrid
    EMAIL_HOST_PASSWORD = _sendgrid_key    # tu API Key
else:
    # 💻 DESARROLLO LOCAL — salida en consola (sin enviar emails reales)
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    EMAIL_HOST = 'smtp.sendgrid.net'   # referencia para cuando se active
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = 'apikey'
    EMAIL_HOST_PASSWORD = _sendgrid_key

DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'TravelHub <noreply@travelhub.ai>')
SERVER_EMAIL = DEFAULT_FROM_EMAIL  # emails de error de Django

# Redes Sociales y Notificaciones
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_ADMIN_ID = os.getenv('TELEGRAM_ADMIN_ID')
TELEGRAM_GROUP_ID = os.getenv('TELEGRAM_GROUP_ID')

# 📱 WhatsApp Microservice (Evolution API / VPS)
WHATSAPP_MICROSERVICE_URL = os.getenv('WHATSAPP_MICROSERVICE_URL', 'http://localhost:3000/send')
WHATSAPP_MICROSERVICE_TOKEN = os.getenv('WHATSAPP_MICROSERVICE_TOKEN')

# GCP - Document AI
GCP_JSON_CREDENTIALS = os.getenv('GCP_JSON_CREDENTIALS') 

# Celery Configuration
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# --- CACHE CONFIGURATION ---
# Usamos Redis para compartir cache entre workers de Gunicorn (importante para debouncing)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/0").replace("/0", "/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
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

ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'ABCh678YourFixedSecretKeyForEncryptionSafetyMakeItLong')

# 🛰️ CONFIGURACIÓN DE SEGURIDAD (HSTS / CSP)
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
X_FRAME_OPTIONS = 'DENY'

# CSP Report-only para testing (luego poner en producción)
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

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
        ],
    },
}

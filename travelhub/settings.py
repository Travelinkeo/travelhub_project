import os
import ssl
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# DEBUG defaults to False for safety. Set DEBUG=True in .env for development.
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# En producción, mostrar errores detallados en logs pero no al usuario
if not DEBUG:
    import logging
    logging.basicConfig(
        level=logging.ERROR,
        format='%(asctime)s [%(levelname)s] %(message)s',
    )

# SECRET_KEY must be set in .env file. We raise an error if it's not found.
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY no está configurada en el entorno. "
        "Por favor, configúrala en tu archivo .env con al menos 50 caracteres."
    )

# Validar fortaleza de SECRET_KEY en producción
if not DEBUG and len(SECRET_KEY) < 50:
    raise RuntimeError(
        "SECRET_KEY debe tener al menos 50 caracteres en producción. "
        "Usa: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
    )

# Permitir acceso desde red local y ngrok
ALLOWED_HOSTS_STRING = os.getenv('ALLOWED_HOSTS', '')
if ALLOWED_HOSTS_STRING:
    ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STRING.split(',') if host.strip()]
else:
    # Defaults para desarrollo local
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '192.168.100.19']

# En desarrollo, permitir dominios ngrok, localtunnel y cloudflare
if DEBUG:
    ALLOWED_HOSTS.extend(['.ngrok-free.app', '.ngrok-free.dev', '.ngrok.io', '.loca.lt', '.trycloudflare.com'])
    # Confiar en ngrok, localtunnel y cloudflare para CSRF
    CSRF_TRUSTED_ORIGINS = [
        'https://*.ngrok-free.app',
        'https://*.ngrok-free.dev',
        'https://*.ngrok.io',
        'https://*.loca.lt',
        'https://*.trycloudflare.com',
    ]
else:
    CSRF_TRUSTED_ORIGINS = []

# Permitir Vercel y Render en producción
ALLOWED_HOSTS.extend(['.vercel.app', 'travelhub-project.onrender.com', 'travelhub-web.onrender.com'])
CSRF_TRUSTED_ORIGINS.extend(['https://*.vercel.app', 'https://travelhub-project.onrender.com', 'https://travelhub-web.onrender.com'])

# Evitar que Django agregue/redirija automáticamente barras finales (previene bucles con proxies/rewrite)
APPEND_SLASH = False

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'cloudinary_storage',  # Cloudinary para archivos media
    'cloudinary',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt.token_blacklist',  # enable blacklist for logout/invalidation
    'corsheaders',  # CORS control
    'drf_spectacular',  # OpenAPI/Swagger documentation
    'personas.apps.PersonasConfig', # App para Cliente y Pasajero
    'cotizaciones.apps.CotizacionesConfig', # App para Cotizaciones
    'contabilidad.apps.ContabilidadConfig', # App para Contabilidad
    'core.apps.CoreConfig',
    'accounting_assistant.apps.AccountingAssistantConfig',
    'django_celery_results',
    'django_extensions',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # debe ir antes de CommonMiddleware para añadir headers
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.RequestMetaAuditMiddleware',  # captura IP/UA para auditoría
    # 'core.middleware.SecurityHeadersMiddleware',  # security headers & CSP report-only
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware_saas.SaaSLimitMiddleware',  # Verificar límites de plan SaaS
]
ROOT_URLCONF = 'travelhub.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [], # Django buscará en la carpeta 'templates' de cada app.
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
WSGI_APPLICATION = 'travelhub.wsgi.application'

# Base de datos: Usar DATABASE_URL (Render/Railway) o configuración manual
import dj_database_url

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'TravelHub'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Caracas'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static',]

# Whitenoise configuration
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True if DEBUG else False

# Cloudinary configuration
import cloudinary
import cloudinary.uploader
import cloudinary.api

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET')
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
USE_CLOUDINARY = os.getenv('USE_CLOUDINARY', 'True') == 'True'

if USE_CLOUDINARY and CLOUDINARY_STORAGE.get('CLOUD_NAME'):
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    print(f"[OK] Cloudinary configurado: {CLOUDINARY_STORAGE['CLOUD_NAME']}")
else:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    print("[WARNING] Usando almacenamiento local (FileSystemStorage)")

# Django 5: usar STORAGES en lugar de STATICFILES_STORAGE (evita deprecation warning)
# IMPORTANTE: 'default' es para archivos media (usar Cloudinary si está configurado)
if USE_CLOUDINARY and CLOUDINARY_STORAGE.get('CLOUD_NAME'):
    STORAGES = {
        "default": {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"},  # PDFs públicos
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

FIXTURE_DIRS = [BASE_DIR / 'fixtures',]

# Gemini API Key
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Sentry Configuration (Monitoreo)
SENTRY_DSN = os.getenv('SENTRY_DSN')
if SENTRY_DSN and not DEBUG:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment=os.getenv('ENVIRONMENT', 'production'),
    )

# Google Cloud Platform settings
GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', '')
GCP_LOCATION = os.getenv('GCP_LOCATION', 'us')
GCP_PROCESSOR_ID = os.getenv('GCP_PROCESSOR_ID', '')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # Prioridad 1: JWT (más seguro)
        'rest_framework.authentication.SessionAuthentication',  # Prioridad 2: Sessions (Django Admin)
        'rest_framework.authentication.TokenAuthentication',  # Prioridad 3: Legacy (deprecado)
    ],
    'DEFAULT_PERMISSION_CLASSES': [],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    # Baseline conservative; can tune via env later.
    'DEFAULT_THROTTLE_RATES': {
        'user': os.getenv('THROTTLE_USER_RATE', '1000/day'),
        'anon': os.getenv('THROTTLE_ANON_RATE', '100/day'),
        'login': os.getenv('THROTTLE_LOGIN_RATE', '100/hour'),  # Aumentado para desarrollo
        'dashboard': '100/hour',
        'liquidacion': '50/hour',
        'reportes': '20/hour',
        'upload': '30/hour',
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'MAX_PAGE_SIZE': 1000,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'TravelHub API',
    'DESCRIPTION': 'API REST completa para gestión de agencia de viajes',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': r'/api/',
}



_JWT_SIGNING_KEY = os.getenv('JWT_SIGNING_KEY', SECRET_KEY)
SIMPLE_JWT = {
    # Duración balanceada: seguridad + UX
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_MINUTES', '30'))),  # 30 min (antes 15)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_DAYS', '7'))),  # 7 días
    'ROTATE_REFRESH_TOKENS': True,  # Rotar refresh token en cada uso (más seguro)
    'BLACKLIST_AFTER_ROTATION': True,  # Invalidar tokens viejos
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),  # Solo Bearer (estándar)
    'SIGNING_KEY': _JWT_SIGNING_KEY,
    'ALGORITHM': os.getenv('JWT_ALGORITHM', 'HS256'),
    # Seguridad adicional
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

def csp_nonce(request):  # pragma: no cover - simple context injection
    return {'csp_nonce': request.META.get('CSP_NONCE')}

# --- CORS Configuration ---
# Explicit allowlist; populate from env CORS_ALLOWED_ORIGINS (comma separated) or sensible defaults for local dev.
_cors_origins_env = os.getenv('CORS_ALLOWED_ORIGINS', '')
if _cors_origins_env:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins_env.split(',') if o.strip()]
else:
    # Default development origins (adjust in production via env)
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:3001',
        'http://127.0.0.1:3001',
        'https://alumni-pensions-sandwich-photographers.trycloudflare.com',
        'https://firmware-traffic-connecting-expectations.trycloudflare.com',
        'https://whole-license-sunday-too.trycloudflare.com',
        'https://hang-kirk-clinton-institution.trycloudflare.com',
    ]

# Agregar Vercel a CORS
CORS_ALLOWED_ORIGINS.append('https://travelhubproject-git-main-travelinkeos-projects.vercel.app')
CORS_ALLOWED_ORIGINS.append('https://travelhubproject.vercel.app')

# Reduce surface: only allow credentials if explicitly enabled
CORS_ALLOW_CREDENTIALS = True

# Allow Authorization header for JWT
CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Optionally restrict headers/methods (defaults generally fine). We keep defaults.

# --- HTTPS / Security Settings (applied when not DEBUG) ---
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
else:
    # En desarrollo, no redirigir a HTTPS para evitar loops con frontend
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# --- Cache & Celery Configuration (PostgreSQL como broker) ---
REDIS_URL = os.getenv('REDIS_URL')
DATABASE_URL = os.getenv('DATABASE_URL')

# Usar PostgreSQL como broker de Celery (más barato que Redis)
if DATABASE_URL:
    # Cache en memoria (suficiente para desarrollo)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'travelhub-cache',
        }
    }
    
    # Usar PostgreSQL como broker de Celery
    CELERY_BROKER_URL = f"db+{DATABASE_URL}"
    CELERY_RESULT_BACKEND = 'django-db'
    CELERY_CACHE_BACKEND = 'django-cache'
    
    print("[OK] Usando PostgreSQL como broker de Celery (económico).")

else:
    # Fallback local
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'travelhub-cache',
        }
    }
    CELERY_BROKER_URL = 'django://'
    CELERY_RESULT_BACKEND = 'django-db'
    CELERY_CACHE_BACKEND = 'django-cache'
    print("[OK] Usando Django como broker de Celery (desarrollo).")


# Common Celery settings
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos

# Configuración específica para PostgreSQL broker
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_RETRY = True

# Celery Beat - Tareas programadas
try:
    from travelhub.celery_beat_schedule import CELERY_BEAT_SCHEDULE
except ImportError:
    CELERY_BEAT_SCHEDULE = {}

# Frontend URL para emails
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# --- Custom App Settings ---

# Lista de correos de proveedores para el Agente Autónomo de Operaciones
SUPPLIER_EMAILS = [
    'proveedor1@example.com',
    'facturacion@proveedor2.com',
    'notificaciones@otroproveedor.com',
]

# Gmail IMAP settings (para leer correos de boletos)
GMAIL_USER = os.getenv('GMAIL_USER', '')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', '')
GMAIL_IMAP_HOST = os.getenv('GMAIL_IMAP_HOST', 'imap.gmail.com')
GMAIL_FROM_KIU = os.getenv('GMAIL_FROM_KIU', 'noreply@kiusys.com')

# WhatsApp / Twilio settings
WHATSAPP_NOTIFICATIONS_ENABLED = os.getenv('WHATSAPP_NOTIFICATIONS_ENABLED', 'False') == 'True'
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', '')  # Formato: +14155238886

# Email settings
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'TravelHub <noreply@travelhub.com>')

# Stripe settings (SaaS billing)
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
STRIPE_PRICE_ID_BASIC = os.getenv('STRIPE_PRICE_ID_BASIC', '')
STRIPE_PRICE_ID_PRO = os.getenv('STRIPE_PRICE_ID_PRO', '')
STRIPE_PRICE_ID_ENTERPRISE = os.getenv('STRIPE_PRICE_ID_ENTERPRISE', '')

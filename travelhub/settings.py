import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# SECRET_KEY must be set in .env file. We raise an error if it's not found.
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in the environment. Please set it in your .env file.")

# DEBUG defaults to False for safety. Set DEBUG=True in .env for development.
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS_STRING = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STRING.split(',')]

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
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt.token_blacklist',  # enable blacklist for logout/invalidation
    'corsheaders',  # CORS control
    'personas.apps.PersonasConfig', # App para Cliente y Pasajero
    'cotizaciones.apps.CotizacionesConfig', # App para Cotizaciones
    'contabilidad.apps.ContabilidadConfig', # App para Contabilidad
    'core.apps.CoreConfig',
    'accounting_assistant.apps.AccountingAssistantConfig',
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
    'core.models.RequestMetaAuditMiddleware',  # captura IP/UA para auditoría
    # 'core.models.SecurityHeadersMiddleware',  # security headers & CSP report-only
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
                'travelhub.settings.csp_nonce',
            ],
        },
    },
]
WSGI_APPLICATION = 'travelhub.wsgi.application'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'TravelHub',
        'USER': 'postgres',
        'PASSWORD': 'Linkeo1331*',
        'HOST': 'localhost',
        'PORT': '5432',
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

# Django 5: usar STORAGES en lugar de STATICFILES_STORAGE (evita deprecation warning)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Durante desarrollo y tests (DEBUG=True) usamos un storage más tolerante para evitar
# fallos en tests que referencian assets no recopilados aún. En producción (DEBUG=False)
# se mantiene el manifest para cache busting.
if DEBUG:
    STORAGES["staticfiles"] = {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"}
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

FIXTURE_DIRS = [BASE_DIR / 'fixtures',]

# Gemini API Key
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # Mantener token legacy temporalmente (deprecate pronto)
        'rest_framework.authentication.TokenAuthentication',
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
        'login': os.getenv('THROTTLE_LOGIN_RATE', '5/min'),
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25
}



_JWT_SIGNING_KEY = os.getenv('JWT_SIGNING_KEY', SECRET_KEY)
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_MINUTES', '15'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_DAYS', '7'))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer', 'JWT'),
    'SIGNING_KEY': _JWT_SIGNING_KEY,
    'ALGORITHM': os.getenv('JWT_ALGORITHM', 'HS256'),
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
    ]

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

# --- Custom App Settings ---

# Lista de correos de proveedores para el Agente Autónomo de Operaciones
SUPPLIER_EMAILS = [
    'proveedor1@example.com',
    'facturacion@proveedor2.com',
    'notificaciones@otroproveedor.com',
]

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Para desarrollo
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # Para producción
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'tu_email@gmail.com'
# EMAIL_HOST_PASSWORD = 'tu_password'
DEFAULT_FROM_EMAIL = 'TravelHub <noreply@travelhub.com>'

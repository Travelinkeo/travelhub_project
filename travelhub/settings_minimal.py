from .settings import *

# Desactivar apps que puedan causar problemas de startup o señales complejas
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core.apps.CoreConfig',
    'apps.bookings.apps.BookingsConfig',
    'apps.finance.apps.FinanceConfig',
    'apps.crm.apps.CrmConfig',
    'apps.common.apps.CommonConfig',
    'apps.contabilidad.apps.ContabilidadConfig',
    'apps.automation.apps.AutomationConfig',
    'apps.cms.apps.CmsConfig',
    'apps.communications.apps.CommunicationsConfig',
    'apps.cotizaciones.apps.CotizacionesConfig',
    'apps.marketing.apps.MarketingConfig',
]

# Desactivar middleware pesado
MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
]

# Usar DB en memoria para makemigrations
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

from .settings import *

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'core.apps.CoreConfig',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

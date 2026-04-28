import os
os.environ['PGCLIENTENCODING'] = 'utf-8'
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
application = get_wsgi_application()

import os

from django.core.wsgi import get_wsgi_application

os.environ["PGCLIENTENCODING"] = "utf-8"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
application = get_wsgi_application()

import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("DELETE FROM django_migrations WHERE (app='crm' AND name >= '0015') OR (app='finance' AND name >= '0009') OR (app='marketing' AND name >= '0006') OR (app='automation' AND name >= '0007')")
    print(f"Deleted {cursor.rowcount} faked migrations.")

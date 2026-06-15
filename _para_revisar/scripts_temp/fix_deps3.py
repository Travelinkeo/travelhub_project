import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("DELETE FROM django_migrations WHERE (app='finance' AND name >= '0007') OR (app='crm' AND name >= '0014') OR (app='marketing' AND name >= '0005') OR (app='automation' AND name >= '0006')")
    print(f"Deleted {cursor.rowcount} faked migrations.")

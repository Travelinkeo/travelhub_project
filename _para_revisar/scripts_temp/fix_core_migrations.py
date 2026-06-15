import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("DELETE FROM django_migrations WHERE app='core' AND name >= '0029'")
    print(f"Deleted {cursor.rowcount} faked migrations from core.")

import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

import importlib
migration = importlib.import_module("apps.bookings.migrations.0036_rename_core_tables_to_bookings")

try:
    migration._reverse_rename_tables(None, None)
    print("Reversed table renames successfully.")
except Exception as e:
    print(f"Error reversing table renames: {e}")

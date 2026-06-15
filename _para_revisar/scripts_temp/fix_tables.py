import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

import importlib

migration = importlib.import_module("apps.bookings.migrations.0036_rename_core_tables_to_bookings")

try:
    migration._rename_tables(None, None)
    print("Renamed tables successfully.")
except Exception as e:
    print(f"Error renaming tables: {e}")

try:
    migration._rename_indexes_and_constraints(None, None)
    print("Renamed indexes successfully.")
except Exception as e:
    print(f"Error renaming indexes: {e}")

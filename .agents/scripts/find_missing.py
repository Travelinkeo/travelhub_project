import os
import sys

sys.path.insert(0, "/app")
os.environ["DJANGO_SETTINGS_MODULE"] = "travelhub.settings"

import django

django.setup()

from django.db import connection

c = connection.cursor()
c.execute(
    "SELECT name, applied FROM django_migrations "
    "WHERE app='core' AND name LIKE '0044%%' ORDER BY name"
)
rows = c.fetchall()
print("=== core 0044 ===")
for r in rows:
    print(r)

c.execute(
    "SELECT name, applied FROM django_migrations "
    "WHERE app='bookings' AND name LIKE '0043%%' ORDER BY name"
)
rows = c.fetchall()
print("=== bookings 0043 ===")
for r in rows:
    print(r)

c.execute(
    "SELECT name, applied FROM django_migrations "
    "WHERE app='bookings' AND name LIKE '0045%%' ORDER BY name"
)
rows = c.fetchall()
print("=== bookings 0045 ===")
for r in rows:
    print(r)

# Also get the full sorted list of applied migrations for core and bookings
c.execute("SELECT name FROM django_migrations WHERE app='core' ORDER BY name")
core = [r[0] for r in c.fetchall()]
print(f"Total core: {len(core)}")

c.execute("SELECT name FROM django_migrations WHERE app='bookings' ORDER BY name")
bookings = [r[0] for r in c.fetchall()]
print(f"Total bookings: {len(bookings)}")

# Now let's see the file-based list
core_files = sorted(
    [
        f.replace(".py", "")
        for f in os.listdir("core/migrations")
        if f.endswith(".py") and f != "__init__"
    ]
)
bookings_files = sorted(
    [
        f.replace(".py", "")
        for f in os.listdir("apps/bookings/migrations")
        if f.endswith(".py") and f != "__init__"
    ]
)

print(f"Core files: {len(core_files)}")
print(f"Bookings files: {len(bookings_files)}")

# Show gaps
for db_name in core:
    if db_name not in core_files:
        print(f"MISSING core file: {db_name}")
for fname in core_files:
    if fname not in core:
        print(f"UNAPPLIED core file: {fname}")

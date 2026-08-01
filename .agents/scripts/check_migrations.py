import os
import sys

# Write output to /tmp/result.txt so we can read it
sys.stdout = open("/tmp/mig_result.txt", "w")  # noqa: S108

import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from django.db.migrations.recorder import MigrationRecorder as MR

core_files = set(
    f.replace(".py", "")
    for f in os.listdir("core/migrations")
    if f.endswith(".py") and f != "__init__"
)
bookings_files = set(
    f.replace(".py", "")
    for f in os.listdir("apps/bookings/migrations")
    if f.endswith(".py") and f != "__init__"
)

core_db = set(m.name for m in MR.Migration.objects.filter(app="core"))
bookings_db = set(m.name for m in MR.Migration.objects.filter(app="bookings"))

print("=== core ===")
print(f"DB records: {len(core_db)}")
print(f"Files: {len(core_files)}")
missing = core_db - core_files
if missing:
    print(f"Missing files for these DB records: {sorted(missing)}")
extra = core_files - core_db
if extra:
    print(f"Unapplied files: {sorted(extra)}")

print("\n=== bookings ===")
print(f"DB records: {len(bookings_db)}")
print(f"Files: {len(bookings_files)}")
missing = bookings_db - bookings_files
if missing:
    print(f"Missing files for these DB records: {sorted(missing)}")
extra = bookings_files - bookings_db
if extra:
    print(f"Unapplied files: {sorted(extra)}")

# Latest per app
print(f"\ncore latest file: {max(core_files)}")
print(f"core latest DB: {max(core_db)}")
print(f"bookings latest file: {max(bookings_files)}")
print(f"bookings latest DB: {max(bookings_db)}")

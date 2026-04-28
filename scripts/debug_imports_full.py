
import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")

print(f"CWD: {os.getcwd()}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")

modules_to_test = [
    'apps',
    'apps.bookings',
    'apps.bookings.models',
    'apps.crm',
    'apps.crm.models',
    'apps.finance',
    'apps.finance.models',
    'apps.cms',
    'apps.cms.models',
    'cotizaciones',
    'cotizaciones.models',
]

for mod in modules_to_test:
    try:
        __import__(mod)
        print(f"[OK] Import successful: {mod}")
    except Exception as e:
        print(f"[FAIL] Import failed: {mod} -> {e}")
        import traceback
        traceback.print_exc()

print("-" * 50)
print("Attempting django.setup()...")
try:
    django.setup()
    print("[OK] django.setup() successful")
except Exception as e:
    print(f"[FAIL] django.setup() failed -> {e}")
    import traceback
    traceback.print_exc()

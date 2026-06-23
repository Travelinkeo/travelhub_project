import os
import time

print("Starting import test...")
start = time.time()
try:
    import django

    # Setup django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
    django.setup()
    print(f"Django setup took: {time.time() - start:.2f}s")

    mid = time.time()
    print(f"Importing apps.crm.models took: {time.time() - mid:.2f}s")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()

print(f"Total time: {time.time() - start:.2f}s")

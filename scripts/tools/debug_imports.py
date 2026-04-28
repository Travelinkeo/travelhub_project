import time
import sys
import os

print("Starting import test...")
start = time.time()
try:
    import django
    from django.conf import settings
    # Setup django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
    django.setup()
    print(f"Django setup took: {time.time() - start:.2f}s")
    
    mid = time.time()
    from apps.crm.models import Cliente
    print(f"Importing apps.crm.models took: {time.time() - mid:.2f}s")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print(f"Total time: {time.time() - start:.2f}s")

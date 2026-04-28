import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

print("Django setup successful.")
print(f"STRIPE_SECRET_KEY exists: {hasattr(settings, 'STRIPE_SECRET_KEY')}")
print(f"STRIPE_SECRET_KEY value: {getattr(settings, 'STRIPE_SECRET_KEY', 'NOT FOUND')[:5]}...")

import os
import django
from django.core.cache import cache

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

print("Clearing Cache...")
cache.clear()
print("Cache Cleared.")

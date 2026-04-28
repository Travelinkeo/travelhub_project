import os
import django
from django.urls import reverse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

try:
    url = reverse('core:ventas_dashboard')
    print(f"Success: {url}")
except Exception as e:
    print(f"Error: {e}")

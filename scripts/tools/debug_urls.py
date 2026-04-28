import os
import django
from django.urls import reverse, get_resolver

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

try:
    url = reverse('core:gds_analyzer')
    print(f"SUCCESS: core:gds_analyzer resolves to {url}")
except Exception as e:
    print(f"ERROR: {e}")

# List all core namespaces
resolver = get_resolver()
print("\nNamespaces found:")
for ns in resolver.namespace_dict:
    print(f"- {ns}")

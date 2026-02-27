import os
import django
import sys
import json

sys.path.append(r"C:\Users\ARMANDO\travelhub_project")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado

b = BoletoImportado.objects.get(pk=417)
print(f"--- COPA DEBUG (ID {b.pk}) ---")
print(json.dumps(b.datos_parseados, indent=2, ensure_ascii=False))

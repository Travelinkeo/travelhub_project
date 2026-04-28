import os
import sys
import django
from django.db.migrations.loader import MigrationLoader
from django.db import connections

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

loader = MigrationLoader(connections['default'])
print("Nodes in Graph:")
for node in loader.graph.nodes:
    if node[0] == 'crm' or node[0] == 'cotizaciones':
        print(f" - {node}")

print("\nApps in graph:")
print(loader.graph.app_names())

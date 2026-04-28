import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

def list_columns(table_name):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
        return [c[0] for c in cursor.fetchall()]

table = 'personas_cliente'
cols = sorted(list_columns(table))
print(f"Total columns: {len(cols)}")
for col in cols:
    print(col)

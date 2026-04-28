import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

def get_columns(table_name):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
        columns = cursor.fetchall()
        return [c[0] for c in columns]

print(f"Columns in core_cliente: {get_columns('core_cliente')}")
print(f"Columns in personas_cliente: {get_columns('personas_cliente')}")
print(f"Columns in crm_cliente: {get_columns('crm_cliente')}")

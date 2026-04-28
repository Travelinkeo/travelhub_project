import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

def table_exists(table_name):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table_name}')")
        return cursor.fetchone()[0]

print(f"Exists crm_cliente: {table_exists('crm_cliente')}")
print(f"Exists personas_cliente: {table_exists('personas_cliente')}")
print(f"Exists core_cliente: {table_exists('core_cliente')}")

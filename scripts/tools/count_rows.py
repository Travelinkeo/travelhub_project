import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

def get_count(table_name):
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]
    except Exception as e:
        return f"Error: {e}"

print(f"Row count in core_cliente: {get_count('core_cliente')}")
print(f"Row count in personas_cliente: {get_count('personas_cliente')}")

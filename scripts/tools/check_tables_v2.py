import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

def table_exists(table_name):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT exists (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')")
        return cursor.fetchone()[0]

tables = ['personas_cliente', 'crm_cliente']
for table in tables:
    print(f"Table {table} exists: {table_exists(table)}")

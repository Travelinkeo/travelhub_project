import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

import sys

table_name = sys.argv[1] if len(sys.argv) > 1 else 'core_itemcotizacion'

with connection.cursor() as cursor:
    cursor.execute(f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = '{table_name}'
    """)
    columns = cursor.fetchall()
    if not columns:
        print(f"Table {table_name} not found or has no columns.")
    for col in columns:
        print(f"{col[0]}: {col[1]}")

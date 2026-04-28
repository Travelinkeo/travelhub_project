
import os
import sys
import django
from django.db import connection

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

def inspect_table(table_name):
    print(f"--- Inspecting {table_name} ---")
    with connection.cursor() as cursor:
        try:
            cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}'")
            rows = cursor.fetchall()
            if not rows:
                print("Table not found or empty.")
            for row in rows:
                print(f" - {row[0]} ({row[1]})")
        except Exception as e:
            print(f"Error inspecting {table_name}: {e}")

inspect_table('personas_cliente')
inspect_table('core_cliente')
inspect_table('core_venta')

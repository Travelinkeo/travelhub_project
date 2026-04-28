import os
import sys
import django
from django.db import connection

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub_project.settings') # Verify settings module name
# Actually, the user's settings are in 'travelhub.settings' usually
os.environ['DJANGO_SETTINGS_MODULE'] = 'travelhub.settings'
django.setup()

def check_table(table_name):
    print(f"\nChecking columns for table: {table_name}")
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}'")
        columns = cursor.fetchall()
        for col in columns:
            print(f" - {col[0]} ({col[1]})")

check_table('personas_pasajero')
check_table('personas_cliente')
check_table('core_pasajero')
check_table('core_cliente')

import os
import sys
import django

# Add the project directory to sys.path
sys.path.append('c:/Users/ARMANDO/travelhub_project')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()
from django.db import connection
table_name = 'personas_pasajero'
with connection.cursor() as cursor:
    cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
    columns = [row[0] for row in cursor.fetchall()]
    print(columns)

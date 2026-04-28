import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.db import connection
from django.contrib.auth.models import User

print("--- BUSCANDO 'dic2' EN DATABASE ---")

cursor = connection.cursor()
cursor.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'")
tables = [row[0] for row in cursor.fetchall()]

for table in tables:
    try:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        for row in rows:
            if 'dic2' in str(row).lower():
                print(f"Match en tabla '{table}': {row}")
    except Exception as e:
        # print(f"Error en tabla {table}: {e}")
        pass

print("--- FIN DE BUSQUEDA ---")

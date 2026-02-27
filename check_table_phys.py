import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

def check_phys_table(table_name):
    print(f"--- PHYSICAL COLUMN LIMITS ({table_name}) ---")
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT column_name, character_maximum_length 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' 
            AND table_schema = 'public'
            ORDER BY column_name
        """)
        rows = cursor.fetchall()
        for r in rows:
            print(f"{r[0]}: {r[1]}")

if __name__ == "__main__":
    check_phys_table('core_migrationcheck')

import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

def check_boleto_phys():
    print("--- PHYSICAL COLUMN LIMITS (core_boletoimportado) ---")
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name, character_maximum_length 
            FROM information_schema.columns 
            WHERE table_name = 'core_boletoimportado' 
            AND table_schema = 'public'
            ORDER BY column_name
        """)
        rows = cursor.fetchall()
        for r in rows:
            print(f"{r[0]}: {r[1]}")

if __name__ == "__main__":
    check_boleto_phys()

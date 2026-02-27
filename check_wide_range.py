import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

def check_wide_range():
    print("--- PHYSICAL COLUMN LIMITS (140-160) ---")
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name, column_name, character_maximum_length 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND character_maximum_length BETWEEN 140 AND 160
            AND data_type = 'character varying'
            ORDER BY table_name, column_name
        """)
        rows = cursor.fetchall()
        for r in rows:
            print(f"{r[0]}.{r[1]}: {r[2]}")

if __name__ == "__main__":
    check_wide_range()

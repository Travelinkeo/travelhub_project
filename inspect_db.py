import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

def inspect():
    with connection.cursor() as cursor:
        print("--- Tables starting with core_ ---")
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'core_%'")
        for row in cursor.fetchall():
            print(row[0])
            
        print("\n--- Tables starting with finance_ ---")
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'finance_%'")
        for row in cursor.fetchall():
            print(row[0])

if __name__ == "__main__":
    inspect()

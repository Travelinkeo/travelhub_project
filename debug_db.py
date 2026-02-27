import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

def list_db_objects():
    with connection.cursor() as cursor:
        print("--- Searching for ANY relation with 'gasto' ---")
        cursor.execute("SELECT relname, relkind FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND relname ILIKE '%gasto%';")
        for row in cursor.fetchall():
            print(f"Relation Found: {row[0]} (Type: {row[1]})")

def cleanup_relations():
    with connection.cursor() as cursor:
        print("\n--- Cleaning up ---")
        # Try to drop the table first which should cascade to indexes
        cursor.execute("DROP TABLE IF EXISTS core_gastooperativo_old CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS core_gastooperativo CASCADE;")
        
        # Cleanup any remaining sequences or orphans
        cursor.execute("SELECT relname, relkind FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND relname ILIKE '%gasto%';")
        rels = cursor.fetchall()
        for r_name, r_kind in rels:
            print(f"Residual found: {r_name} ({r_kind}). Dropping...")
            if r_kind == 'i':
                cursor.execute(f"DROP INDEX IF EXISTS {r_name} CASCADE;")
            elif r_kind == 'S':
                cursor.execute(f"DROP SEQUENCE IF EXISTS {r_name} CASCADE;")

if __name__ == "__main__":
    list_db_objects()
    cleanup_relations()

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.db import connection

def verify():
    with connection.cursor() as cursor:
        cursor.execute("SELECT indexname FROM pg_indexes WHERE indexname LIKE 'idx_%'")
        indices = [row[0] for row in cursor.fetchall()]
        print("Existing indices:")
        for idx in sorted(indices):
            print(f"- {idx}")

if __name__ == "__main__":
    verify()

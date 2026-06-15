import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.db import connection
from apps.bookings.models import Venta

table_name = Venta._meta.db_table
with connection.cursor() as cursor:
    cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}';")
    db_columns = {row[0] for row in cursor.fetchall()}

model_columns = {f.column for f in Venta._meta.fields}

missing = model_columns - db_columns
print('Missing columns in DB:', missing)


import os
import sys
import django
from django.db import transaction, connection

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from apps.crm.models import Cliente
from apps.bookings.models import Venta
from apps.bookings.models import Venta as VentaApp # Check if they are same

print(f"Core Venta: {Venta}")
print(f"Apps Venta: {VentaApp}")
print(f"Cliente table: {Cliente._meta.db_table}")

try:
    with transaction.atomic():
        print("Creating Client...")
        c = Cliente.objects.create(nombres="Test", apellidos="Debug", email="testdebug@example.com")
        print(f"Client created: ID {c.pk}")
        
        # Check if it exists in DB via SQL
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT id_cliente FROM {Cliente._meta.db_table} WHERE id_cliente = %s", [c.pk])
            row = cursor.fetchone()
            print(f"SQL Verification: Found ID {row[0] if row else 'NONE'}")
            
        print("Creating Venta...")
        v = Venta.objects.create(
            localizador=f"TEST-{c.pk}", 
            cliente=c,
            moneda_id=1 # Assuming USD exists
        )
        print(f"Venta create: ID {v.pk}")
        
        # Force rollback to clean up
        raise Exception("Force Rollback")

except Exception as e:
    print(f"Caught: {e}")

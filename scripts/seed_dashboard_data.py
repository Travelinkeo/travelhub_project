import os
import sys
import django
import random
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import Venta, ItemVenta
from core.models import Moneda, ProductoServicio, Proveedor, Aerolinea, Ciudad, Pais
from core.models import Pasajero, Cliente

def seed_data():
    print("Seeding dashboard data for 2026...")
    
    # Ensure catalogs exist
    moneda, _ = Moneda.objects.get_or_create(codigo_iso="USD", defaults={'nombre': 'Dolar', 'simbolo': '$'})
    cliente, _ = Cliente.objects.get_or_create(nombres="Cliente Demo", apellidos="Test", defaults={'cedula_identidad': 'V-12345678'})
    proveedor, _ = Proveedor.objects.get_or_create(nombre="Proveedor Demo")
    producto, _ = ProductoServicio.objects.get_or_create(nombre="Boleto Aéreo", codigo_interno="TKT001", defaults={'tipo_producto': 'AIR'})
    # Pais creation handled below
    # Pais creation

    ciudad_orig, _ = Ciudad.objects.get_or_create(nombre="Caracas", defaults={'pais': pais})
    ciudad_dest, _ = Ciudad.objects.get_or_create(nombre="Madrid", defaults={'pais': pais})
    
    # Create ~10 sales for different months in 2026
    current_year = timezone.now().year
    from datetime import datetime
    start_date = datetime(current_year, 1, 1, tzinfo=timezone.get_current_timezone())
    
    for month in range(1, 13):
        if month > timezone.now().month + 1: break # Don't go too far into future
        
        # Create 1-3 sales per month
        for _ in range(random.randint(1, 3)):
            sale_date = start_date.replace(month=month, day=random.randint(1, 28))
            
            amount = Decimal(random.randint(500, 2000))
            
            venta = Venta.objects.create(
                cliente=cliente,
                fecha_venta=sale_date,
                moneda=moneda,
                estado=random.choice([Venta.EstadoVenta.PAGADA_TOTAL, Venta.EstadoVenta.CONFIRMADA]),
                total_venta=amount, # Explicitly setting total for simplicity
                subtotal=amount,
                descripcion_general=f"Venta Demo {month}/{current_year}"
            )
            
            # Create dummy item
            ItemVenta.objects.create(
                venta=venta,
                producto_servicio=producto,
                cantidad=1,
                precio_unitario_venta=amount,
                total_item_venta=amount,
                subtotal_item_venta=amount,
                proveedor_servicio=proveedor
            )
            
            print(f"Created Venta {venta.localizador} for {amount} on {sale_date.date()}")

    print("Seeding complete.")

if __name__ == "__main__":
    seed_data()

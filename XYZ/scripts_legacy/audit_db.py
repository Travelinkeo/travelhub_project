
import os
import django
from django.db.models import Count, Q

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models import (
    Venta, BoletoImportado, Cliente, Proveedor, Factura,
    ItemVenta, AsientoContable
)
from core.models.personas import Pasajero

def audit_database():
    print("=== Database Audit Report ===")
    
    # 1. Counts
    print("\n[COUNTS]")
    print(f"Ventas: {Venta.objects.count()}")
    print(f"Boletos Importados: {BoletoImportado.objects.count()}")
    print(f"Clientes: {Cliente.objects.count()}")
    print(f"Facturas: {Factura.objects.count()}")
    print(f"Pasajeros: {Pasajero.objects.count()}")

    # 2. Orphans (Boletos without Venta)
    orphaned_boletos = BoletoImportado.objects.filter(venta_asociada__isnull=True).count()
    print(f"\n[ORPHANS] Boletos without Venta: {orphaned_boletos}")
    
    # 3. Data Integrity
    # Ventas without Cliente
    ventas_no_client = Venta.objects.filter(cliente__isnull=True).count()
    print(f"[INTEGRITY] Ventas without Cliente: {ventas_no_client}")
    
    # Ventas with 0 total but items exist
    ventas_zero_total = Venta.objects.filter(total_venta=0).annotate(num_items=Count('items_venta')).filter(num_items__gt=0).count()
    print(f"[INTEGRITY] Ventas $0.00 with Items: {ventas_zero_total}")

    # 4. Storage/Bloat
    # Check for heavy text fields (naive check)
    print("\n[POTENTIAL BLOAT]")
    # Cannot easily check size in SQL via Django without raw queries, skipping size check.
    
    # 5. Duplicates (Naive check on Boletos)
    print("\n[DUPLICATES]")
    # Boletos with same number
    dupes = BoletoImportado.objects.values('numero_boleto').annotate(cnt=Count('id_boleto_importado')).filter(cnt__gt=1)
    if dupes.exists():
        print(f"Found {dupes.count()} duplicate Ticket Numbers.")
        for d in dupes[:5]:
            print(f" - {d['numero_boleto']} ({d['cnt']} times)")
    else:
        print("No duplicate ticket numbers found.")

if __name__ == "__main__":
    audit_database()

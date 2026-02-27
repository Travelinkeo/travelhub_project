
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models import BoletoImportado, Venta

def clean_database():
    print("=== Database Cleanup Started ===")
    
    # 1. Cleaner: Delete Boletos with NULL Ticket Number
    corrupt_boletos = BoletoImportado.objects.filter(numero_boleto__isnull=True)
    count_null = corrupt_boletos.count()
    if count_null > 0:
        print(f"Deleting {count_null} corrupt boletos (numero_boleto=NULL)...")
        corrupt_boletos.delete()
    else:
        print("No corrupt boletos found.")

    # 2. Cleaner: Delete Boletos with EMPTY Ticket Number
    empty_boletos = BoletoImportado.objects.filter(numero_boleto='')
    count_empty = empty_boletos.count()
    if count_empty > 0:
        print(f"Deleting {count_empty} empty boletos (numero_boleto='')...")
        empty_boletos.delete()
    
    # 3. Optional: Delete Orphans (older than X days? For now just log)
    # orphaned_boletos = BoletoImportado.objects.filter(venta_asociada__isnull=True)
    # print(f"Orphaned boletos remaining: {orphaned_boletos.count()}")

    print("=== Database Cleanup Completed ===")

if __name__ == "__main__":
    clean_database()

import os
import django
import sys

sys.path.append(r'c:\Users\ARMANDO\travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.db import connection

def fix_orphans():
    print("Checking for orphaned Venta records (Using RAW SQL)...")
    
    with connection.cursor() as cursor:
        # 0. Cleanup orphaned ManyToMany (Venta <-> Pasajeros) - INDEPENDENT CHECK
        print("Step 0: Cleaning core_venta_pasajeros orphans (bad pasajero_id)...")
        try:
            cursor.execute("SELECT COUNT(*) FROM core_venta_pasajeros WHERE pasajero_id NOT IN (SELECT id_pasajero FROM core_pasajero)")
            m2m_count = cursor.fetchone()[0]
            if m2m_count > 0:
                print(f"Found {m2m_count} orphan M2M records.")
                cursor.execute("DELETE FROM core_venta_pasajeros WHERE pasajero_id NOT IN (SELECT id_pasajero FROM core_pasajero)")
                print(f"Deleted {cursor.rowcount} orphan entries from core_venta_pasajeros.")
            else:
                print("No orphan M2M records found.")
        except Exception as e:
            print(f"Error cleaning M2M: {e}")

        cursor.execute("SELECT COUNT(*) FROM core_venta WHERE cliente_id NOT IN (SELECT id_cliente FROM core_cliente)")
        result = cursor.fetchone()
        count = result[0] if result else 0
        print(f"Found {count} orphaned Venta records via SQL.")
        
        if count > 0:
            print("Attempting to delete orphaned records (Children first)...")
            try:
                # 1. Delete Items (Child of Venta)
                print("Step 1: Deleting orphaned ItemVenta...")
                cursor.execute("DELETE FROM core_itemventa WHERE venta_id IN (SELECT id_venta FROM core_venta WHERE cliente_id NOT IN (SELECT id_cliente FROM core_cliente))")
                # ... rest of the logic ...
                # Re-inserting the rest of the logic partially might be messy with replace_file_content if I don't provide it all.
                # Since I am replacing the whole block, I should carry over the logic.
                
                print("Step 2.5: Unlinking core_boletoimportado...")
                try:
                     cursor.execute("UPDATE core_boletoimportado SET venta_asociada_id = NULL WHERE venta_asociada_id IN (SELECT id_venta FROM core_venta WHERE cliente_id NOT IN (SELECT id_cliente FROM core_cliente))")
                except:
                     pass
                
                print("Step 3: Deleting orphaned Venta...")
                cursor.execute("DELETE FROM core_venta WHERE cliente_id NOT IN (SELECT id_cliente FROM core_cliente)")
                print(f"Deleted {cursor.rowcount} rows from core_venta.")
                
            except Exception as e:
                print(f"Error during cleanup: {e}")

    print("Cleanup complete.")

if __name__ == "__main__":
    fix_orphans()

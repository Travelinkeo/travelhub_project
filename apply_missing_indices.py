import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.db import connection

queries = [
    # Core / AuditLog
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    "CREATE INDEX IF NOT EXISTS idx_audit_desc_gin ON core_auditlog USING gin (descripcion gin_trgm_ops)",
    "CREATE INDEX IF NOT EXISTS idx_audit_desc_simple ON core_auditlog (descripcion)",
    
    # CRM
    "CREATE INDEX IF NOT EXISTS idx_pasajero_soft_delete_saas ON crm_pasajero (is_deleted, agencia_id)",
    "CREATE INDEX IF NOT EXISTS idx_cliente_soft_delete_saas ON crm_cliente (is_deleted, agencia_id)",

    # Finance
    "CREATE INDEX IF NOT EXISTS idx_concil_estado ON finance_conciliacionboleto (estado)",
    "CREATE INDEX IF NOT EXISTS idx_concil_soft_delete_saas ON finance_conciliacionboleto (is_deleted, agencia_id)",
    "CREATE INDEX IF NOT EXISTS idx_comisionvta_sd_saas ON finance_comisionventa (is_deleted, agencia_id)",
    "CREATE INDEX IF NOT EXISTS idx_factura_soft_delete_saas ON finance_factura (is_deleted, agencia_id)",
    "CREATE INDEX IF NOT EXISTS idx_gasto_soft_delete_saas ON finance_gastooperativo (is_deleted, agencia_id)",
    "CREATE INDEX IF NOT EXISTS idx_itemfact_soft_delete_saas ON finance_itemfactura (is_deleted, agencia_id)",
    "CREATE INDEX IF NOT EXISTS idx_liqagente_sd_saas ON finance_liquidacionagente (is_deleted, agencia_id)",
    "CREATE INDEX IF NOT EXISTS idx_reglacom_sd_saas ON finance_reglacomision (is_deleted, agencia_id)"
]

def apply():
    with connection.cursor() as cursor:
        for q in queries:
            print(f"Executing: {q}")
            try:
                cursor.execute(q)
            except Exception as e:
                print(f"Error: {e}")
    print("All missing indices applied.")

if __name__ == "__main__":
    apply()

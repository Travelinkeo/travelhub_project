import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.db import connection

indices_to_drop = [
    "idx_audit_desc_gin",
    "idx_audit_desc_simple",
    "idx_audit_descripcion",
    "idx_itemventa_soft_delete_saas",
    "idx_venta_soft_delete_saas",
    "idx_cliente_soft_delete_saas",
    "idx_pasajero_soft_delete_saas",
    "idx_concil_estado",
    "idx_concil_soft_delete_saas",
    "idx_comisionvta_sd_saas",
    "idx_factura_soft_delete_saas",
    "idx_gasto_soft_delete_saas",
    "idx_itemfact_soft_delete_saas",
    "idx_liqagente_sd_saas",
    "idx_reglacom_sd_saas",
    "idx_segmento_soft_delete_saas",
    "idx_actividad_soft_delete_saas",
    "idx_alojam_soft_delete_saas",
    "idx_auto_soft_delete_saas",
    "idx_evento_soft_delete_saas",
    "idx_traslado_soft_delete_saas"
]

def cleanup():
    with connection.cursor() as cursor:
        for idx in indices_to_drop:
            print(f"Dropping {idx} if exists...")
            cursor.execute(f"DROP INDEX IF EXISTS {idx}")
    print("Cleanup done.")

if __name__ == "__main__":
    cleanup()

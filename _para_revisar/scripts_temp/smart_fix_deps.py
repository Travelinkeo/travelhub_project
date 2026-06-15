import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder

# Don't fail on missing migrations to build the graph
loader = MigrationLoader(connection, ignore_no_migrations=True)

# Build a map of applied migrations
recorder = MigrationRecorder(connection)
applied_migrations = recorder.applied_migrations()

# We deleted core >= 0029 and bookings >= 0025.
# Let's see what is in applied_migrations that depends on them.
deleted_migrations = {
    ('core', '0029_alter_anulacionboleto_agencia_and_more'),
    ('core', '0030_venta_monto_neto_proveedor_venta_monto_venta_cliente_and_more'),
    ('core', '0031_fix_missing_db_columns'),
    ('core', '0032_alter_actividadservicio_agencia_and_more'),
    ('core', '0033_add_facturafiscal_agencia'),
    ('core', '0034_alter_anulacionboleto_agencia_and_more'),
    ('core', '0035_alter_actividadservicio_managers_and_more'),
    ('core', '0036_alter_actividadservicio_table_and_more'),
    ('core', '0037_alter_feeventa_venta_alter_pagoventa_venta'),
    ('core', '0038_rename_core_tables_to_bookings'),
    ('core', '0039_tarifarioproveedor_add_agencia_proveedor'),
    ('core', '0040_add_missing_fk_and_softdelete_columns'),
    ('core', '0041_add_hoteltarifario_amenidades_m2m'),
    ('core', '0042_add_missing_indexes'),
    ('core', '0043_productoservicio_requiere_datos_pasajero_especificos_and_more'),
    ('core', '0044_alter_actividadservicio_incluye_and_more'),
    ('bookings', '0025_boletoimportado_raw_hash'),
    ('bookings', '0026_alter_venta_factura_consolidada'),
    ('bookings', '0027_boletoimportadotransito'),
    ('bookings', '0028_venta_alerta_tl_disparada_and_more'),
    ('bookings', '0029_venta_monto_neto_proveedor_venta_monto_venta_cliente_and_more'),
    ('bookings', '0030_fix_missing_db_columns'),
    ('bookings', '0031_alter_actividadservicio_agencia_and_more'),
    ('bookings', '0032_add_facturafiscal_agencia'),
    ('bookings', '0033_alter_actividadservicio_managers_and_more'),
    ('bookings', '0034_alter_actividadservicio_table_and_more'),
    ('bookings', '0035_alter_feeventa_venta_alter_pagoventa_venta'),
    ('bookings', '0036_rename_core_tables_to_bookings'),
    ('bookings', '0037_tarifarioproveedor_add_agencia_proveedor'),
    ('bookings', '0038_add_missing_fk_and_softdelete_columns'),
    ('bookings', '0039_add_hoteltarifario_amenidades_m2m'),
    ('bookings', '0040_add_missing_indexes'),
    ('bookings', '0041_productoservicio_requiere_datos_pasajero_especificos_and_more'),
    ('bookings', '0042_alter_actividadservicio_incluye_and_more'),
}

# Add all their descendants to a set of bad nodes
bad_nodes = set()
for node in loader.graph.nodes:
    if node in applied_migrations:
        # Check if any dependency of `node` is in deleted_migrations
        # forwards_plan includes the node itself and all its dependencies
        try:
            plan = loader.graph.forwards_plan(node)
            if any(dep in deleted_migrations for dep in plan):
                bad_nodes.add(node)
        except Exception as e:
            # If graph is broken, we might get an exception. Try manually checking dependencies
            pass

print(f"Found {len(bad_nodes)} broken migrations to remove from history:")
for n in sorted(bad_nodes):
    print(n)

with connection.cursor() as cursor:
    for app, name in bad_nodes:
        cursor.execute("DELETE FROM django_migrations WHERE app=%s AND name=%s", [app, name])
    
print("Cleanup complete.")

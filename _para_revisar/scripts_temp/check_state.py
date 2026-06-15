import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from django.db import connections
from django.db.migrations.executor import MigrationExecutor

connection = connections['default']
executor = MigrationExecutor(connection)

node = executor.loader.graph.nodes[('bookings', '0026_alter_venta_factura_consolidada')]
dependencies = node.dependencies

from_state = executor.loader.project_state(dependencies)
to_state = from_state.clone()

migration = executor.loader.get_migration('bookings', '0026_alter_venta_factura_consolidada')
migration.operations[0].state_forwards('bookings', to_state)

from_model = from_state.apps.get_model('bookings', 'Venta')
to_model = to_state.apps.get_model('bookings', 'Venta')
from_field = from_model._meta.get_field('factura_consolidada')
to_field = to_model._meta.get_field('factura_consolidada')

print("Old model field in from_state:")
print(f"  model: {from_field.remote_field.model}")
print(f"  type: {type(from_field.remote_field.model)}")

print("New model field in to_state:")
print(f"  model: {to_field.remote_field.model}")
print(f"  type: {type(to_field.remote_field.model)}")

# Let's inspect the entire _meta of from_state and to_state for bookings.Venta
print("\nChecking from_state bookings.Venta fields:")
for f in from_model._meta.fields:
    if f.remote_field:
         print(f"  {f.name}: to={f.remote_field.model} (type={type(f.remote_field.model)})")

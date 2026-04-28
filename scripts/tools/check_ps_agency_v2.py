from core.models_catalogos import ProductoServicio
# If all_objects is not readily available like that, we can use the manager explicitly
try:
    mgr = ProductoServicio.all_objects
except AttributeError:
    mgr = ProductoServicio.objects # Fallback but might be filtered

print(f'Total: {mgr.count()}')
for ps in mgr.all():
    print(f'- {ps.id_producto_servicio}: {ps.nombre} ({ps.tipo_producto}) | Agencia: {ps.agencia_id}')

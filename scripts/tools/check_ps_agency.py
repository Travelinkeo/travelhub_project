from core.models_catalogos import ProductoServicio
print(f'Total: {ProductoServicio.objects.all_objects.count()}')
for ps in ProductoServicio.objects.all_objects.all():
    print(f'- {ps.id_producto_servicio}: {ps.nombre} ({ps.tipo_producto}) | Agencia: {ps.agencia_id}')

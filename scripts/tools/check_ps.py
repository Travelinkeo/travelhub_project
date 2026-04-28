from core.models_catalogos import ProductoServicio
print(f'Total: {ProductoServicio.objects.count()}')
print(f'AIR: {ProductoServicio.objects.filter(tipo_producto="AIR").count()}')
for ps in ProductoServicio.objects.all()[:10]:
    print(f'- {ps.id_producto_servicio}: {ps.nombre} ({ps.tipo_producto})')

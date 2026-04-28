from core.models_catalogos import ProductoServicio
print(f'First AIR: {ProductoServicio.objects.filter(tipo_producto="AIR").first()}')
print(f'Absolute First: {ProductoServicio.objects.first()}')

from apps.bookings.models import ProductoServicio

for ps in ProductoServicio.all_objects.all():
    print(f"{ps.id_producto_servicio}: {ps.nombre} | AG: {ps.agencia_id}")

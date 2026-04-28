import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.crm.models import Cliente

try:
    clientes = Cliente.objects.all()[:5]
    print(f"Consulta a Cliente exitosa! Se encontraron {len(clientes)} clientes.")
    for c in clientes:
        print(f"Cliente: {c.nombres} - ID: {c.id_cliente}")
except Exception as e:
    print(f"Error al consultar clientes: {e}")

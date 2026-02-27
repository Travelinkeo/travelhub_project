
import os
import django
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.crm.models import Cliente
from core.models import Venta

def check_client():
    try:
        v = Venta.objects.get(pk=157)
        c = v.cliente
        print(f"Cliente ID: {c.pk}")
        print(f"Nombres: '{c.nombres}' (Len: {len(c.nombres)})")
        print(f"Apellidos: '{c.apellidos}' (Len: {len(c.apellidos)})")
        
        doc = c.numero_documento
        print(f"Documento (Prop): '{doc}' (Len: {len(doc)})")
        
        tel = c.telefono
        print(f"Telefono (Prop): '{tel}' (Len: {len(tel)})")
        
        dir1 = c.direccion_linea1 or ''
        print(f"Direccion: '{dir1}' (Len: {len(dir1)})")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_client()

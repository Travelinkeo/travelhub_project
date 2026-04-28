import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models.agencia import Agencia

try:
    agencias = Agencia.objects.all()
    for ag in agencias:
        print(f"ID: {ag.pk}, Nombre: {ag.nombre}")
        # Try to access fields that might have issues
        print(f"  Direccion: {ag.direccion}")
        print(f"  Ciudad: {ag.ciudad}")
        print(f"  Pais: {ag.pais}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

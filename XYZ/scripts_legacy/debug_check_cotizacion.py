
import os
import django
import sys

sys.path.append(r'c:\Users\ARMANDO\travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from cotizaciones.models import Cotizacion

def check_cotizacion():
    pk = 7
    try:
        cot = Cotizacion.objects.get(pk=pk)
        print(f"✅ Cotizacion {pk} EXISTS.")
        print(f"  Numero: {cot.numero_cotizacion}")
        print(f"  Cliente: {cot.cliente}")
        print(f"  Consultor: {cot.consultor}")
        print(f"  Estado: {cot.estado}")
    except Cotizacion.DoesNotExist:
        print(f"❌ Cotizacion {pk} DOES NOT EXIST.")
        
    last = Cotizacion.objects.last()
    if last:
        print(f"Last Cotizacion ID: {last.pk} ({last.numero_cotizacion})")

if __name__ == '__main__':
    check_cotizacion()

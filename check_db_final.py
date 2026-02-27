
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
django.setup()

from apps.bookings.models import BoletoImportado

def check():
    qs = BoletoImportado.objects.filter(localizador_pnr__icontains='WKTOTQ')
    count = qs.count()
    print(f"Final DB Count for WKTOTQ: {count}")
    for b in qs:
        print(f" - ID: {b.pk}, Name: {b.nombre_pasajero_completo}")

if __name__ == '__main__':
    check()

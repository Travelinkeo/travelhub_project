
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import BoletoImportado

def dump():
    qs = BoletoImportado.objects.order_by('-fecha_subida')[:20]
    with open('recent_tickets.txt', 'w', encoding='utf-8') as f:
        f.write(f"Total Boletos: {BoletoImportado.objects.count()}\n")
        f.write("-" * 50 + "\n")
        for b in qs:
            f.write(f"ID: {b.pk}\n")
            f.write(f"PNR: {b.localizador_pnr}\n")
            f.write(f"Name: {b.nombre_pasajero_completo}\n")
            f.write(f"File: {b.archivo_boleto.name}\n")
            f.write(f"Fecha: {b.fecha_subida}\n")
            f.write("-" * 50 + "\n")

if __name__ == '__main__':
    dump()

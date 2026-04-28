import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import BoletoImportado

print("Last 10 Boletos:")
for b in BoletoImportado.objects.order_by('-pk')[:10]:
    print(f"ID: {b.pk}, PNR: {b.localizador_pnr}, Estado: {b.estado_parseo}, PDF: {bool(b.archivo_pdf_generado)}, Log: {b.log_parseo[:100]}...")

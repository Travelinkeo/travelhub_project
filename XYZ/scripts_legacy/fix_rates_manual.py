import os
import django
from decimal import Decimal
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models_catalogos import TipoCambio, Moneda
from contabilidad.models import TasaCambioBCV

print("--- Force Updating Rates ---")

# 1. Get Official Truth
bcv_truth = TasaCambioBCV.objects.order_by('-fecha').first()
if not bcv_truth:
    print("CRITICAL: No TasaCambioBCV found!")
    exit(1)

tasa_real = bcv_truth.tasa_bsd_por_usd
fecha_real = bcv_truth.fecha or date.today()
print(f"Official Rate from BCV: {tasa_real} ({fecha_real})")

# 2. Get Monedas
usd = Moneda.objects.get(codigo_iso='USD')
ves = Moneda.objects.filter(codigo_iso='VES').first()
ved = Moneda.objects.filter(codigo_iso='VED').first()

def update_pair(origen, destino, tasa, fecha):
    if not origen or not destino:
        print(f"Skipping pair {origen} -> {destino} (Missing currency)")
        return
        
    obj, created = TipoCambio.objects.update_or_create(
        moneda_origen=origen,
        moneda_destino=destino,
        fecha_efectiva=fecha,
        defaults={
            'tasa_conversion': tasa
        }
    )
    print(f"Updated {origen.codigo_iso} -> {destino.codigo_iso}: {tasa} ({'Created' if created else 'Updated'})")

# 3. Update VES (Soberano)
update_pair(usd, ves, tasa_real, fecha_real)

# 4. Update VED (Digital/Local? - Just in case)
update_pair(usd, ved, tasa_real, fecha_real)

print("--- Done ---")

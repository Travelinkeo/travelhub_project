import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models_catalogos import TipoCambio, Moneda
from django.utils import timezone

print("--- Debugging BCV Rate Logic ---")

# 1. Check Moneda Local
local_currency = Moneda.objects.filter(es_moneda_local=True).first()
print(f"Moneda Local: {local_currency.codigo_iso if local_currency else 'None'}")

# 2. Check USD and VES
usd = Moneda.objects.filter(codigo_iso='USD').first()
ves = Moneda.objects.filter(codigo_iso='VES').first()
print(f"USD: {usd}, VES: {ves}")

# 3. Check Latest Rates for USD -> Local
if usd and local_currency:
    rate_local = TipoCambio.objects.filter(
        moneda_origen=usd,
        moneda_destino=local_currency
    ).order_by('-fecha_efectiva', '-id_tipo_cambio').first()
    
    if rate_local:
        print(f"Latest USD -> {local_currency.codigo_iso}: {rate_local.tasa_conversion} (Date: {rate_local.fecha_efectiva})")
    else:
        print(f"No rate found for USD -> {local_currency.codigo_iso}")

# 4. Check Latest Rates for USD -> VES (Fallback)
if usd and ves:
    rate_ves = TipoCambio.objects.filter(
        moneda_origen=usd,
        moneda_destino=ves
    ).order_by('-fecha_efectiva', '-id_tipo_cambio').first()
    
    if rate_ves:
        print(f"Latest USD -> VES: {rate_ves.tasa_conversion} (Date: {rate_ves.fecha_efectiva})")
    else:
        print("No rate found for USD -> VES")

# 5. Check TasaCambioBCV (Source of Truth)
from contabilidad.models import TasaCambioBCV
bcv_truth = TasaCambioBCV.objects.order_by('-fecha').first()
if bcv_truth:
    print(f"TasaCambioBCV (Official Truth): {bcv_truth.tasa_bsd_por_usd} (Date: {bcv_truth.fecha})")
else:
    print("No TasaCambioBCV records found")

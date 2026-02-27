import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models_catalogos import TipoCambio, Moneda

local = Moneda.objects.filter(es_moneda_local=True).first()
if local:
    print(f"Moneda Local: {local.nombre} ({local.codigo_iso}) ID: {local.pk}")
else:
    print("NO HAY MONEDA LOCAL")

ves = Moneda.objects.filter(codigo_iso='VES').first()
if ves:
    print(f"Moneda VES: {ves.nombre} ID: {ves.pk} Local: {ves.es_moneda_local}")

usd_rates = TipoCambio.objects.filter(moneda_origen__codigo_iso='USD')
for r in usd_rates:
    print(f"Tasa: USD -> {r.moneda_destino.codigo_iso} ({r.moneda_destino.pk})")

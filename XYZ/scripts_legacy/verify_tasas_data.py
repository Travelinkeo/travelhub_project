import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models_catalogos import TipoCambio, Moneda

print("--- Verificando Monedas ---")
monedas = Moneda.objects.all()
for m in monedas:
    print(f"Moneda: {m.nombre} ({m.codigo_iso}) - Local: {m.es_moneda_local}")

print("\n--- Verificando Tipos de Cambio (USD) ---")
usd_tasas = TipoCambio.objects.filter(moneda_origen__codigo_iso='USD').order_by('-fecha_efectiva')
print(f"Total tasas USD encontradas: {usd_tasas.count()}")
for t in usd_tasas[:5]:
    print(f"USD -> {t.moneda_destino.codigo_iso}: {t.tasa_conversion} ({t.fecha_efectiva})")

print("\n--- Verificando Query del Dashboard ---")
moneda_local = Moneda.objects.filter(es_moneda_local=True).first()
if not moneda_local:
    print("WARNING: No hay moneda local definida!")

usd_qs = TipoCambio.objects.filter(moneda_origen__codigo_iso='USD')
if moneda_local:
    usd_qs = usd_qs.filter(moneda_destino=moneda_local)
    
obj = usd_qs.order_by('-fecha_efectiva', '-id_tipo_cambio').first()
print(f"Resultado Query Dashboard (USD): {obj.tasa_conversion if obj else 'None'}")

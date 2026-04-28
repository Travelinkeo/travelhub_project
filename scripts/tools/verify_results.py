import os
import django
from decimal import Decimal
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()
from apps.crm.models_freelancer import FreelancerProfile, ComisionFreelancer
from apps.bookings.models import BoletoImportado

f = FreelancerProfile.objects.get(usuario__username='agente_freelancer')
print(f"💰 AGENTE: {f.usuario.username}")
print(f"🏦 SALDO WALLET: ${f.saldo_por_cobrar}")

comisiones = ComisionFreelancer.objects.filter(freelancer=f).order_by('-creado_en')
print(f"📋 Comisiones (Últimas 5):")
for c in comisiones[:5]:
    v = c.venta
    print(f" - Venta {v.localizador} | Total: ${v.total_venta} | Comisión: ${c.monto_comision_ganada}")

boletos = BoletoImportado.objects.all().order_by('-fecha_subida')[:3]
print(f"🎫 Últimos Boletos:")
for b in boletos:
    print(f" - ID {b.pk} | {b.archivo_boleto.name} | Estado: {b.estado_parseo} | Formato: {b.formato_detectado}")

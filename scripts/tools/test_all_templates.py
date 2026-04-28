import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from django.template.loader import render_to_string
from core.models import Agencia

templates_to_test = [
    'core/tickets/golden_ticket_v2.html',
    'core/tickets/ticket_template_kiu_bolivares.html',
    'core/tickets/ticket_template_sabre.html',
    'core/tickets/ticket_template_copa_sprk.html',
    'core/tickets/ticket_template_tk_connect.html',
    'core/tickets/ticket_template_wingo.html',
    'core/tickets/variations/editorial_plus.html',
    'core/tickets/variations/executive_compact.html',
    'core/tickets/variations/modern_tech.html',
    'core/tickets/variations/timeline_pro.html',
    'vouchers/variations/v1_golden_classic.html',
    'vouchers/variations/v2_editorial.html',
    'vouchers/variations/v3_executive.html',
    'vouchers/variations/v4_timeline.html',
    'vouchers/variations/v5_modern.html',
]

try:
    agencia = Agencia.objects.first()
except:
    agencia = None

with open("test_results_3.txt", "w", encoding="utf-8") as f:
    for t in templates_to_test:
        try:
            render_to_string(t, {'agencia': agencia, 'pasajero': {}, 'itinerario': {}, 'reserva': {}, 'boleto': {}, 'flight': {}, 'venta': {'pasajeros': {}}})
            f.write(f"OK: {t}\n")
        except Exception as e:
            f.write(f"FAIL: {t} - {e}\n")

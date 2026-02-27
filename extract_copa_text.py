
import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import BoletoImportado
from core.services.ticket_parser_service import TicketParserService

boleto = BoletoImportado.objects.get(pk=1059)
print(f"Boleto ID: {boleto.pk}")
print(f"File Path: {boleto.archivo_boleto.path}")

service = TicketParserService()
text = service._extraer_texto(boleto)

with open('debug_text_1059_copa.txt', 'w', encoding='utf-8') as f:
    f.write(text or "EMPTY TEXT")

print("✅ Text saved to debug_text_1059_copa.txt")


import os
import django
import sys
import logging

# Setup Django Environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import BoletoImportado
from core.services.ticket_parser_service import TicketParserService

boleto = BoletoImportado.objects.get(pk=1050)
print(f"Boleto File Path: {boleto.archivo_boleto.path}")

if os.path.exists(boleto.archivo_boleto.path):
    # Simulate the extraction
    service = TicketParserService()
    texto_extraido = service._extraer_texto(boleto)
    
    with open('debug_text_1050.txt', 'w', encoding='utf-8') as f:
        f.write(texto_extraido or "")
    
    print("✅ Text extracted to debug_text_1050.txt")
else:
    print("❌ File not found on disk")

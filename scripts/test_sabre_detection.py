import os
import sys
import django

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.ticket_parser import extract_data_from_text

# Text from ID 985
text = """Recibo de boleto electrónico
Preparado para
COHEN CABELLO/NAIDALY DEL CARMEN
CÓDIGO DE RESERVACIÓN LUXWOQ
"""

print(f"Original Text Length: {len(text)}")
print(f"Upper Text: {text.upper()}")

data = extract_data_from_text(text)

print(f"\n--- RESULTS ---")
print(f"Detected System: {data.get('SOURCE_SYSTEM')}")
print(f"Data keys: {list(data.keys())}")

if data.get('SOURCE_SYSTEM') == 'SABRE':
    print("✅ SUCCESS: Detected as SABRE")
else:
    print("❌ FAILURE: Detected as KIU/Compatible")
    
    # Debug detection conditions
    plain_text_upper = text.upper()
    cond1 = ('ETICKET RECEIPT' in plain_text_upper or 'RECIBO DE PASAJE' in plain_text_upper or 'RECIBO DE BOLETO' in plain_text_upper)
    cond2 = ('RESERVATION CODE' in plain_text_upper or 'CODIGO DE RESERVA' in plain_text_upper or 'CODIGO DE RESERVACION' in plain_text_upper or 'CÓDIGO DE RESERVA' in plain_text_upper or 'CÓDIGO DE RESERVACIÓN' in plain_text_upper)
    
    print(f"\nDebug Conditions:")
    print(f"Cond 1 (Receipt labels): {cond1}")
    print(f"Cond 2 (Reservation labels): {cond2}")
    
    print(f"\nTesting specific matches:")
    print(f"'RECIBO DE BOLETO' in Text: {'RECIBO DE BOLETO' in plain_text_upper}")
    print(f"'CÓDIGO DE RESERVACIÓN' in Text: {'CÓDIGO DE RESERVACIÓN' in plain_text_upper}")


import re
from typing import Dict, Any
from decimal import Decimal

def extract_amounts(text: str) -> Dict[str, Any]:
    amounts = {}
    
    # Buscar Total
    patterns_total = [
        r'Total Amount\s*[:]?\s*([A-Z]{3})\s*([\d,.]+)',
        r'Total\s*[:]?\s*([A-Z]{3})\s*([\d,.]+)',
        r'Monto Total\s*[:]?\s*([A-Z]{3})\s*([\d,.]+)',
        r'Grand Total\s*[:]?\s*([A-Z]{3})\s*([\d,.]+)'
    ]
    
    currency = None
    total = None
    
    for p in patterns_total:
        print(f"Testing pattern: {p}")
        match = re.search(p, text, re.IGNORECASE)
        if match:
            print(f"MATCH: {match.group(0)}")
            currency = match.group(1)
            total_str = match.group(2).replace(',', '') 
            try:
                total = str(Decimal(total_str))
                break
            except: pass
    
    if total:
        amounts['total_amount'] = total
        amounts['currency'] = currency
        amounts['total'] = total # Legacy
        amounts['total_currency'] = currency
        
    return amounts

text_spanish = """
    Boleto Electrónico para ANDRES FELIPE GOMEZ
    Número de Documento: 2302013874530
    Fecha de Emisión: 04FEB26
    
    Total Amount: USD 500.00
    Taxes: USD 50.00
"""

print(f"\n--- DEBUG RESULT ---\n{extract_amounts(text_spanish)}")

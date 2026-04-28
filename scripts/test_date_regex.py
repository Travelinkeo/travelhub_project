import re

def _get_fecha_emision(texto: str) -> str:
    patterns = [
        r'ISSUE DATE/FECHA DE EMISION\s*[:\s]*([0-9]{1,2}\s+[A-Z]{3}\s+[0-9]{4}\s+[0-9]{2}:[0-9]{2})',
        r'ISSUE DATE\s*[:\s]*([0-9]{1,2}\s+[A-Z]{3}\s+[0-9]{4}\s+[0-9]{2}:[0-9]{2})',
        # New Attempt
        r'FECHA DE EMISION\s*[:\s]*([0-9]{1,2}\s+[A-Z]{3}\s+[0-9]{4}\s+[0-9]{2}:[0-9]{2})'
    ]
    
    for p in patterns:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            return m.group(1)
            
    return "No encontrado"

# Line from murillo_clean.txt
soto_header = "INTERNET V0 ISSUE DATE/FECHA DE EMISION: 29 JAN 2026 15:51"

print(f"Result: {_get_fecha_emision(soto_header)}")

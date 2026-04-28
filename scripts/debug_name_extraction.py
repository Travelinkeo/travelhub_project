
import re
import sys
import os
import django
from bs4 import BeautifulSoup

# Mocking the function from ticket_parser.py
def _extract_field_single_line(texto: str, patterns: list, default='No encontrado') -> str:
    for pattern in patterns:
        match = re.search(pattern, texto, re.IGNORECASE)
        if match:
            try:
                val = match.group(1).strip()
            except IndexError:
                val = match.group(0).strip()
            # Limpieza extra
            val = re.sub(r'<[^>]+>', '', val)
            val = val.replace('&nbsp;', ' ').strip()
            val = val.rstrip('<>').strip()
            return val
    return default

def _get_nombre_completo_pasajero(texto: str) -> str:
    blacklist = [
        'DATE/FECHA', 'FECHA/EMISION', 'NAME/NOMBRE', 'AGENT/AGENTE', 'FROM/TO', 'DESDE/HACIA', 'AIR/FARE', 
        'TELEFONO', 'PHONE', 'MAIL', 'CORREO', 'DOCUMENTO',
        'FECHA DE EMISION', 'DATE OF ISSUE', 'FECHA', 'DATE'
    ]
    
    # Estrategia 1: Hola, NAME
    match_hola = re.search(r'(?:Hola|Estimado|Hello|Dear)\s*[,:]?\s*([A-Z/ ]{3,})(?:\.|,)', texto, re.IGNORECASE)
    if match_hola:
        candidate = match_hola.group(1).strip()
        print(f"DEBUG: Hola match found: '{candidate}'")
        # Check blacklist
        if len(candidate) > 2 and not any(bad in candidate.upper() for bad in blacklist):
             # return candidate.upper()  <-- This might be returning "YEISON" prematurely!
             print(f"DEBUG: Hola strategy accepted: {candidate}")
             pass # Don't return yet for debugging

    # Estrategia 2: GDS Priority
    matches = re.finditer(r'\b([A-Z]{2,}(?: [A-Z]+)*/[A-Z]{2,}(?: [A-Z]+)*)\b', texto)
    for match in matches:
        candidate = match.group(1).strip()
        if len(candidate) > 5 and not re.search(r'\d', candidate):
            if not any(bad in candidate.upper() for bad in blacklist):
                 print(f"DEBUG: GDS Strategy found: {candidate}")
                 # return candidate

    # Estrategia 3: Name label
    val = _extract_field_single_line(texto, [
        r'NAME/NOMBRE\s*[:\s]*(.+)', 
        r'NAME\s*[:\s]*(.+)',
        r'NOMBRE DEL PASAJERO\s*[:\s]*(.+)'
    ])
    print(f"DEBUG: Label Strategy found: {val}")
    return "MOCKED_RETURN"

def test_file():
    path = 'c:\\Users\\ARMANDO\\travelhub_project\\media\\boletos_importados\\2026\\02\\email_ticket_b1243.html'
    if not os.path.exists(path):
        print("File not found")
        return

    with open(path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    plain_text = soup.get_text(separator='\n')
    
    print("--- PLAIN TEXT DUMP START ---")
    print(plain_text)
    print("--- PLAIN TEXT DUMP END ---")
    
    _get_nombre_completo_pasajero(plain_text)

if __name__ == "__main__":
    test_file()


import re

def _extract_passenger_name_debug(text):
    def extract_field(text, patterns):
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match: return match.group(1).strip()
        return 'No encontrado'

    raw = extract_field(text, [
            r'NAME:\s*([A-ZÁÉÍÓÚÑ/ (),.-]{3,})',
            r'NAME/NOMBRE\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,})',
            r'NAME\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,})',
            r'NOMBRE DEL PASAJERO\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,})',
            r'PASAJERO\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,})',
            r'NOMBRE\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,})'
        ])
    
    print(f"DEBUG RAW: '{raw}'")
    
    if raw == 'No encontrado':
        return raw
    
    stop_tokens = ['FOID', 'RIF', 'ID', 'PASSPORT', 'VUELO', 'FLIGHT', 'TICKET', 
                  'CIUDAD', 'CARACAS', 'BOGOTA', 'LIMA', 'QUITO', 'PANAMA']
    
    upper_raw = raw.upper()
    cut_positions = []
    
    for token in stop_tokens:
        idx = upper_raw.find(token)
        if idx != -1 and idx > 5:
            cut_positions.append(idx)
    
    par_idx = raw.find('(')
    if par_idx != -1 and par_idx > 4:
        cut_positions.append(par_idx)
    
    if cut_positions:
        raw = raw[:min(cut_positions)].rstrip()
        print(f"DEBUG CUT: '{raw}'")
    
    raw = re.sub(r'[^A-ZÁÉÍÓÚÑ/ ]+', ' ', raw.upper())
    raw = re.sub(r'\s{2,}', ' ', raw).strip()
    
    print(f"DEBUG CLEANED: '{raw}'")
    
    if '/' not in raw:
        return raw
    
    apellidos, nombres = raw.split('/', 1)
    nombres = nombres.strip()
    
    location_tokens = {'CARACAS', 'BOGOTA', 'LIMA', 'QUITO', 'PANAMA', 'CIUDAD', 'DE'}
    nombres = re.sub(r'(?:CIUDAD DE [A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,})*)$', '', nombres).strip()
    
    tokens = nombres.split()
    if len(tokens) > 1:
        for i in range(1, len(tokens)):
            tail = tokens[i:]
            if tail and all(t in location_tokens for t in tail):
                tokens = tokens[:i]
                break
        else:
            if tokens[-1] in location_tokens:
                tokens = tokens[:-1]
    
    nombres_limpios = ' '.join(tokens)
    nombres_limpios = re.sub(r'\s{2,}', ' ', nombres_limpios).strip()
    
    return f"{apellidos.strip()}/{nombres_limpios}"

text_sample = """
AGENCIA: CCS00V0WV
NAME: GOMEZ ZULUAGA/CARLOS MARIO
FOID: NI84414910
"""

print(f"RESULT: {_extract_passenger_name_debug(text_sample)}")

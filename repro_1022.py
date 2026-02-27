import re
from typing import List, Dict, Any, Optional, Tuple

def _normalize_and_clean_content(plain_text: str, html_text: str = None) -> str:
    text = plain_text
    text = text.replace("=\r\n", "").replace("=\n", "")
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    return text.strip()

def _extract_field_single_line(texto: str, patterns: list, default='No encontrado') -> str:
    for pattern in patterns:
        match = re.search(pattern, texto, re.IGNORECASE | re.MULTILINE)
        if match:
             return match.group(1).strip()
    return default

stop_keywords = r"FOID|TICKET|NBR|NRO|DATE|FECHA|EMISION|ISSUE|AGENT|AGENTE|REF|RECORD|LOCALIZADOR|PNR|ISSUING|CONTACT|PHONE"

# --- FUNCIONES A PROBAR ---

def get_name(texto):
    patterns = [
        r"\b(?:NAME/NOMBRE|NAME|NOMBRE|PASAJERO)\b\s*[:\s]*((?:(?!\s*\b(?:" + stop_keywords + r")\b[:\s]).)+)",
        r"\b(?:NAME/NOMBRE|NAME|NOMBRE|PASAJERO)\b\s*[:\s]*([^\n\r]+)"
    ]
    name = _extract_field_single_line(texto, patterns)
    if name != 'No encontrado':
        name = re.split(r'\s+\b(?:' + stop_keywords + r')\b[:\s]', name, flags=re.IGNORECASE)[0]
    return name.strip()

def get_fecha(texto):
    return _extract_field_single_line(texto, [
        r'(?:ISSUE DATE|FECHA DE EMISION|EMITIDO EL)\s*[:\s]*(.+)', 
        r'DATE/FECHA\s*[:\s]*(.+)'
    ])

def get_agente(texto):
    return _extract_field_single_line(texto, [
        r'(?:ISSUE AGENT|AGENTE EMISOR|AGENTE)\s*[:\s]*(.+)', 
    ])

def get_foid(texto):
    return _extract_field_single_line(texto, [
        r'\b(?:FOID/D\.IDENTIDAD|FOID|DOCUMENTO)\b\s*[:\s]*([^ \n\r]+)',
        r'\bID\b\s*:\s*([^ \n\r]+)',
    ])

# --- TEST DATA (from normalized_1010.txt) ---
text_1010 = """
Naidaly Cohen 0412-331.23.14 ---------- Forwarded message --------- De: no_config Date: jue, 19 feb 2026 a las 17:34 Subject: E-TICKET ITINERARY RECEIPT - CASTANO NINO/SEBASTIAN To: ELECTRONIC TICKET 
 PASSENGER ITINERARY RECEIPT TICKET NBR: 3080201395574 
 RECIBO DE ITINERARIO DE PASAJEROS BOLETO NRO: 
 INTERNET V0 ISSUE DATE/FECHA DE EMISION: 19 FEB 2026 17:33
 INTERNET ISSUE AGENT/AGENTE EMISOR: CCS00V0WV
 INTERNET 
 INTERNET, VENEZUELA 
 OFFICE ID: VE-22441-0 
 TELEPHONE/TELEFONO: VE-17788-0 
 MAIL INFO: 
 ISSUING AIRLINE/LINEA AEREA EMISORA : CONVIASA
 ADDRESS/DIRECCION : AV. INTERCOMUNAL AEROPUERTO INTERNACIONAL DE MAIQUETIA EDO. LA GUAIRA VENEZUELA TELF +58 0500 266 8427
 RIF : G-20007774-3 
 TICKET NUMBER/NRO DE BOLETO : 308-0201395574
 NAME: CASTANO NINO/SEBASTIAN 
 FOID: PPAX026389 
 BOOKING REF./CODIGO DE RESERVA: C1/ WKTOTQ 
 DESDE/HACIA VUELO CL FECHA HORA HORA BASE TARIFARIA EQP. ESTATUS
  MATURIN V0 272 O 25FEB 0950 1130 OPROMO 23K OK 
  MARACAIBO 
"""

print(f"--- REPRODUCING FAILURES ---")
print(f"NAME: {get_name(text_1010)!r}")
print(f"FECHA: {get_fecha(text_1010)!r}")
print(f"AGENT: {get_agente(text_1010)!r}")
print(f"FOID: {get_foid(text_1010)!r}")

# --- FIX PROPOSAL ---
def get_field_v3(texto, labels):
    label_pattern = r"\b(?:" + "|".join(labels) + r")\b"
    pattern = label_pattern + r"\s*[:\s/]*((?:(?!\s*\b(?:" + stop_keywords + r")\b[:\s]).)+)"
    val = _extract_field_single_line(texto, [pattern])
    if val != 'No encontrado':
        # Remove leading junk like labels that were skipped by lookahead but matched by .
        # Actually the lookahead prevents matching THEM, but what if they are part of the match?
        # e.g. "ISSUE DATE/FECHA DE EMISION" -> "ISSUE DATE" matches, "/FECHA DE EMISION" is captured.
        # We need to clean the result from any word in labels that might be there.
        for lbl in labels:
            val = re.sub(r'^[\s/]*' + re.escape(lbl) + r'[:\s]*', '', val, flags=re.IGNORECASE)
    return val.strip()

print(f"\n--- PROPOSED V3 ---")
print(f"FECHA FIXED: {get_field_v3(text_1010, ['ISSUE DATE', 'FECHA DE EMISION', 'EMITIDO EL'])!r}")
print(f"AGENT FIXED: {get_field_v3(text_1010, ['ISSUE AGENT', 'AGENTE EMISOR', 'AGENTE'])!r}")

# --- ITINERARY REPRO ---
conviasa_pattern = re.compile(r'^([A-Z \.]+)\s+([A-Z0-9]{2}\s*\d{3,4})\s+([A-Z])\s+(\d{1,2}[A-Z]{3})\s+(\d{4})\s+(\d{4})(.*)')
line_maturin = "  MATURIN V0 272 O 25FEB 0950 1130 OPROMO 23K OK "
m = conviasa_pattern.search(line_maturin.strip()) # Search works better than match if there are spaces
print(f"\nITINERARY SEARCH (MATURIN): {'MATCH' if m else 'FAIL'}")
if m: print(f"  Groups: {m.groups()}")

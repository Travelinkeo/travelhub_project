
import re
import os

file_path = r'c:\Users\ARMANDO\travelhub_project\core\ticket_parser.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. FIX TK CONNECT LOGIC
# Pattern matches the old permissive IF block including the linebreak and the indented next line
tk_pattern = re.compile(
    r"(\s+if \('IDENTIFICACIÓN DEL PEDIDO' in plain_text_upper and 'TURKISH AIRLINES' in plain_text_upper\) or \\\s*\n\s+\('GRUPO SOPORTE GLOBAL' in plain_text_upper and 'TURKISH' in plain_text_upper\):)",
    re.MULTILINE
)

tk_replacement = r"""
    # Heurística para TK Connect (Turkish Airlines) - MUY ESPECÍFICA
    # Eliminamos chequeo de 'GRUPO SOPORTE GLOBAL' porque genera falsos positivos con Sabre.
    if 'IDENTIFICACIÓN DEL PEDIDO' in plain_text_upper and ('TK CONNECT' in plain_text_upper or 'TURKISH AIRLINES' in plain_text_upper):"""

if tk_pattern.search(content):
    print("Found TK Connect pattern. Replacing...")
    content = tk_pattern.sub(tk_replacement, content)
else:
    print("WARNING: TK Connect pattern NOT found. Manual check required.")


# 2. FIX COPA LOGIC
copa_pattern = re.compile(
    r"(\s+if \('COPA AIRLINES' in plain_text_upper and 'LOCALIZADOR DE RESERVA' in plain_text_upper\) or 'SPRK' in plain_text_upper:)",
    re.MULTILINE
)

copa_replacement = r"""
    # Heurística para COPA SPRK
    # Evitar capturar boletos de GDS (Sabre/Amadeus) que sean de Copa
    is_gds_signature = 'SABRE' in plain_text_upper or 'AMADEUS' in plain_text_upper or 'RECIBO DE PASAJE ELECTRÓNICO' in plain_text_upper
    
    if (('COPA AIRLINES' in plain_text_upper and 'LOCALIZADOR DE RESERVA' in plain_text_upper) or 'SPRK' in plain_text_upper) and \
       (not is_gds_signature or 'SPRK' in plain_text_upper):"""

if copa_pattern.search(content):
    print("Found Copa pattern. Replacing...")
    content = copa_pattern.sub(copa_replacement, content)
else:
    print("WARNING: Copa pattern NOT found.")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Finished updates.")

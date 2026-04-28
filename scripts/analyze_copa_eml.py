#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para analizar boletos COPA y extraer patrones"""
from email import policy
from email.parser import BytesParser
from pathlib import Path

# Analizar un EML de COPA
eml_path = r"C:\Users\ARMANDO\Downloads\Boletos\COPA\Itinerary for Record Locator KW23RU.eml"
output_file = r"c:\Users\ARMANDO\travelhub_project\copa_sample_text.txt"

with open(eml_path, 'rb') as f:
    msg = BytesParser(policy=policy.default).parse(f)
    
    plain_text = ""
    html_text = ""
    
    for part in msg.walk():
        if part.get_content_type() == 'text/plain':
            plain_text = part.get_content()
        elif part.get_content_type() == 'text/html':
            html_text = part.get_content()

# Guardar texto plano
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("TEXTO PLANO\n")
    f.write("="*80 + "\n")
    f.write(plain_text or "No hay texto plano")
    f.write("\n\n" + "="*80 + "\n")
    f.write("HTML (primeros 2000 caracteres)\n")
    f.write("="*80 + "\n")
    f.write((html_text or "No hay HTML")[:2000])

print(f"Texto extraído y guardado en: {output_file}")
print(f"\nBuscando campos clave...")

# Buscar patrones de interés
for line in (plain_text or "").split('\n')[:50]:
    if any(word in line.upper() for word in ['LOCALIZADOR', 'LOCATOR', 'TICKET', 'BOLETO', 'PASAJERO', 'PASSENGER', 'TOTAL', 'PRECIO']):
        print(f"  -> {line.strip()}")

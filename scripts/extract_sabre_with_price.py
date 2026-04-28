#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para extraer texto completo de PDF SABRE con precio"""
import pdfplumber

file_path = r"C:\Users\ARMANDO\Downloads\Boletos\WINGO\Recibo de pasaje electrónico, 13 marzo para OSCAR DUQUE.pdf"
output_file = r"c:\Users\ARMANDO\travelhub_project\sabre_with_price.txt"

with pdfplumber.open(file_path) as pdf:
    full_text = ""
    for page in pdf.pages:
        full_text += page.extract_text() + "\n\n"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(full_text)

print(f"Texto extraído y guardado en: {output_file}")
print(f"Total de caracteres: {len(full_text)}")

# Buscar líneas con precio
print("\n" + "="*80)
print("LÍNEAS CON INFORMACIÓN DE PRECIO:")
print("="*80)
for line in full_text.split('\n'):
    if any(word in line.upper() for word in ['TOTAL', 'TARIFA', 'FARE', 'USD', 'COP', 'PRECIO', 'AMOUNT']):
        if any(char.isdigit() for char in line):
            print(f"→ {line.strip()}")

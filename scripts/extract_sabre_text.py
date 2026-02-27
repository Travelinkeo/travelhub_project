#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para extraer texto completo de PDF SABRE"""
import pdfplumber

file_path = r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 22 mayo para MAURICIO ISAZA.pdf"
output_file = r"c:\Users\ARMANDO\travelhub_project\sabre_sample_text.txt"

with pdfplumber.open(file_path) as pdf:
    full_text = ""
    for page in pdf.pages:
        full_text += page.extract_text() + "\n\n"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(full_text)

print(f"Texto extraído y guardado en: {output_file}")
print(f"Total de caracteres: {len(full_text)}")

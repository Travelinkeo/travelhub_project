#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para extraer y analizar contenido de un PDF SABRE"""
import pdfplumber

file_path = r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 22 mayo para MAURICIO ISAZA.pdf"

print("="*80)
print(f"Analizando: {file_path}")
print("="*80)

with pdfplumber.open(file_path) as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        print(f"\n--- PÁGINA {i+1} ---")
        
        # Buscar líneas que contengan "Total" o "TOTAL"
        lines = text.split('\n')
        for j, line in enumerate(lines):
            if 'TOTAL' in line.upper() or 'TARIFA' in line.upper() or 'FARE' in line.upper():
                # Mostrar contexto (2 líneas antes y 2 después)
                start = max(0, j-2)
                end = min(len(lines), j+3)
                print(f"\nContexto alrededor de línea {j}:")
                for k in range(start, end):
                    prefix = ">>> " if k == j else "    "
                    print(f"{prefix}{lines[k]}")

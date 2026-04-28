#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para buscar 'Total' en múltiples PDFs SABRE"""
import pdfplumber
from pathlib import Path

sabre_dir = Path(r"C:\Users\ARMANDO\Downloads\Boletos\SABRE")
pdfs = list(sabre_dir.glob("*.pdf"))[:10]  # Primeros 10

print(f"Analizando {len(pdfs)} PDFs de SABRE...\n")

for pdf_path in pdfs:
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() or ""
        
        # Buscar palabras clave de precio
        has_total = 'TOTAL' in full_text.upper()
        has_tarifa = 'TARIFA' in full_text.upper() or 'FARE' in full_text.upper()
        has_usd = 'USD' in full_text or '$' in full_text
        
        status = "✅" if (has_total or has_tarifa or has_usd) else "❌"
        
        print(f"{status} {pdf_path.name[:50]}")
        if has_total or has_tarifa or has_usd:
            # Mostrar líneas con precios
            for line in full_text.split('\n'):
                if any(word in line.upper() for word in ['TOTAL', 'TARIFA', 'FARE', 'USD', 'PRECIO']):
                    if any(char.isdigit() for char in line):
                        print(f"   → {line.strip()}")
        print()

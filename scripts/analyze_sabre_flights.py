#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Analizar formato de vuelos en PDF SABRE"""
import pdfplumber

pdf_path = r"C:\Users\ARMANDO\Downloads\Recibo de pasaje electrónico, 19 noviembre para ALIKY DE SOUSA.pdf"

with pdfplumber.open(pdf_path) as pdf:
    text = '\n'.join([p.extract_text() or '' for p in pdf.pages])

print("="*80)
print("ANÁLISIS DE FORMATO DE VUELOS - SABRE")
print("="*80)

# Buscar líneas que contengan información de vuelos
flight_keywords = ['AV', 'AVIANCA', 'AEROVIAS', 'CONFIRMADO', 'TURISTA', 'BUSINESS']
flight_lines = []

for line in text.split('\n'):
    if any(keyword in line.upper() for keyword in flight_keywords):
        flight_lines.append(line)

print("\nLíneas relacionadas con vuelos:")
print("-"*80)
for i, line in enumerate(flight_lines[:20], 1):  # Primeras 20 líneas
    print(f"{i:2}. {line}")

print("\n" + "="*80)
print("TEXTO COMPLETO (primeros 2000 caracteres):")
print("="*80)
print(text[:2000])

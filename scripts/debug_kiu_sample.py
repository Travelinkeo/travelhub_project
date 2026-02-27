#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para extraer y mostrar contenido de un boleto KIU"""
from email import policy
from email.parser import BytesParser

file_path = r"C:\Users\ARMANDO\Downloads\Boletos\KIU\E-TICKET ITINERARY RECEIPT - DUQUE ECHEVERRI_ALEXANDER.eml"

with open(file_path, 'rb') as f:
    msg = BytesParser(policy=policy.default).parse(f)
    
    for part in msg.walk():
        if part.get_content_type() == 'text/plain':
            text = part.get_content()
            print("="*80)
            print("PLAIN TEXT CONTENT:")
            print("="*80)
            print(text[:3000])
            break

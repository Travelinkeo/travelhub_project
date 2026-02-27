#!/usr/bin/env python
"""Script para configurar datos de imprenta digital"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import Agencia

# Obtener la agencia (ajusta el ID si tienes varias)
agencia = Agencia.objects.first()

if agencia:
    # Configurar datos de imprenta digital
    agencia.imprenta_digital_nombre = "Imprenta Digital C.A."
    agencia.imprenta_digital_rif = "J-50456785-5"
    agencia.imprenta_digital_providencia = "SNAT/2024/24555"
    agencia.es_sujeto_pasivo_especial = False  # Cambiar a True si aplica
    agencia.esta_inscrita_rtn = True  # Registro Turístico Nacional
    agencia.save()
    
    print("[OK] Configuración guardada exitosamente:")
    print(f"   Agencia: {agencia.nombre}")
    print(f"   Imprenta: {agencia.imprenta_digital_nombre}")
    print(f"   RIF Imprenta: {agencia.imprenta_digital_rif}")
    print(f"   Providencia: {agencia.imprenta_digital_providencia}")
    print(f"   Contribuyente Especial: {'Sí' if agencia.es_sujeto_pasivo_especial else 'No'}")
    print(f"   Inscrita RTN: {'Sí' if agencia.esta_inscrita_rtn else 'No'}")
else:
    print("[ERROR] No se encontró ninguna agencia. Crea una primero en el admin.")

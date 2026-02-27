#!/usr/bin/env python
"""Script para registrar una retención ISLR de ejemplo"""

import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import FacturaConsolidada
from core.models.retenciones_islr import RetencionISLR
from personas.models import Cliente

# Obtener factura y cliente
factura = FacturaConsolidada.objects.first()
cliente = factura.cliente if factura else Cliente.objects.first()

if not factura or not cliente:
    print("[ERROR] No hay facturas o clientes en el sistema")
    exit(1)

# Crear retención de ejemplo
retencion = RetencionISLR.objects.create(
    numero_comprobante="RET-2025-001",
    factura=factura,
    cliente=cliente,
    fecha_operacion=factura.fecha_emision,
    tipo_operacion='CM',  # Comisiones Mercantiles
    codigo_concepto='03-04',
    base_imponible=factura.subtotal,  # Base antes de IVA
    porcentaje_retencion=Decimal('5.00'),
    # monto_retenido se calcula automáticamente
)

print("[OK] Retención ISLR registrada exitosamente:")
print(f"   Número: {retencion.numero_comprobante}")
print(f"   Factura: {retencion.factura.numero_factura}")
print(f"   Cliente: {retencion.cliente}")
print(f"   Base Imponible: ${retencion.base_imponible}")
print(f"   Porcentaje: {retencion.porcentaje_retencion}%")
print(f"   Monto Retenido: ${retencion.monto_retenido}")
print(f"   Estado: {retencion.get_estado_display()}")

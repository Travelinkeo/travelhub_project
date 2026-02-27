import os
import django
from django.template.loader import render_to_string
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import Venta, Cliente, ItemVenta, BoletoImportado

# Create dummy context objects if they don't exist, just for class structure emulation
class MockCliente:
    numero_documento = "12345678"
    tipo_documento = "V"
    nombres = "Test"
    apellidos = "User"
    email = "test@example.com"
    telefono = "555-1234"

    id_venta = "999"
    pk = 999
    id = 999
    cliente = MockCliente()
    estado = "PEN"
    fecha_venta = None
    subtotal = 100.00
    impuestos = 16.00
    total_venta = 116.00
    monto_pagado = 0
    saldo_pendiente = 116.00
    fees_venta = []
    
    def get_estado_display(self):
        return "Pendiente"

class MockItem:
    producto_servicio = type('obj', (object,), {'nombre': 'Test Item'})
    precio_unitario_venta = 50.00
    total_item_venta = 100.00
    cantidad = 2
    descripcion_personalizada = None

try:
    context = {
        'venta': MockVenta(),
        'items': [MockItem()],
        'boletos': [],
        'pagos': [],
        'current_agency': {'nombre': 'Test Agency', 'logo': None}
    }
    
    rendered = render_to_string('core/erp/ventas/detalle.html', context)
    
    print("--- RENDER SUCCESS ---")
    if "{{ venta.cliente.numero_documento }}" in rendered:
        print("FAIL: Found literal tag {{ venta.cliente.numero_documento }}")
    elif "V 12345678" in rendered:
        print("PASS: Found rendered value 'V 12345678'")
    else:
        print("WARN: Neither literal tag nor value found. Maybe structure changed?")
        
    if "{{ item.precio_unitario_venta" in rendered:
        print("FAIL: Found literal tag {{ item.precio_unitario_venta ... }}")
    else:
        print("PASS: Item tags seem processed.")
        
except Exception as e:
    print(f"--- RENDER ERROR ---")
    print(e)

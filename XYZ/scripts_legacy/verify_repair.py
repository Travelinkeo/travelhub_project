import os
import django
from django.core.files.base import ContentFile
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models.boletos import BoletoImportado
from core.models import Venta
from core.services.parsing import trigger_boleto_parse_service

print("🚀 Iniciando Simulación de Reparación...")

# 1. Crear Boleto Mock
boleto = BoletoImportado(
    estado_parseo=BoletoImportado.EstadoParseo.PENDIENTE
)
# Simulamos un PDF KIU
contenido_mock = b"""
KIUSYS.COM
PASSENGER ITINERARY RECEIPT
NAME: PEREZ/JUAN
BOOKING REF: ABC123
TICKET NO: 1234567890
TOTAL: USD 100.00
"""
boleto.archivo_boleto.save('simulacion_kiu.txt', ContentFile(contenido_mock))
boleto.save()

print(f"✅ Boleto creado: ID {boleto.pk}")

# 2. El signal debería haberse disparado (si fuera real) o llamamos a mano para simular
# En test real, post_save dispara. Aquí, al guardar arriba con archivo, ya disparó.
# Refresh
boleto.refresh_from_db()
print(f"Estado tras guardado: {boleto.estado_parseo}")
print(f"Log: {boleto.log_parseo}")
print(f"Venta Asociada: {boleto.venta_asociada}")

if boleto.venta_asociada:
    venta = boleto.venta_asociada
    print(f"✅ Venta Creada: ID {venta.pk}")
    print(f"    - Cliente: {venta.cliente}")
    print(f"    - Estado: {venta.estado}")
    print(f"    - Notas: {venta.notas}")
    if venta.items_venta.exists():
        item = venta.items_venta.first()
        print(f"✅ Item Creado: {item.descripcion_personalizada}")
        print(f"    - Precio: {item.precio_unitario_venta}")
        print(f"    - Costo: {item.costo_neto_proveedor}")
    else:
        print("❌ ERROR: Venta creada sin items.")
else:
    print("❌ ERROR: No se creó la Venta.")

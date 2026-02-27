
import os
import django
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import Venta
from core.services.facturacion_service import FacturacionService
from apps.finance.models import Factura

def debug_create_invoice_for_sale(sale_id):
    try:
        print(f"Buscando Venta con PK={sale_id}")
        venta = Venta.objects.get(pk=sale_id)
        print(f"Venta encontrada: {venta.localizador} (ID: {venta.pk})")
        print(f"Estado Venta: {venta.estado}")
        print(f"Cliente: {venta.cliente}")
        print(f"Tiene Factura?: {venta.factura}")
        
        if venta.factura:
            print(f"La venta YA tiene factura: {venta.factura} (PK: {venta.factura.pk})")
            return

        print("Intentando generar factura...")
        factura = FacturacionService.generar_factura_desde_venta(venta, venta.cliente)
        print(f"Factura generada exitosamente: {factura} (PK: {factura.pk})")
        print(f"Estado Factura: {factura.estado}")
        
    except Venta.DoesNotExist:
        print(f"Error: Venta con PK={sale_id} no existe.")
    except Exception as e:
        print(f"Error al generar factura: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Try ID 157 from screenshot URL
    debug_create_invoice_for_sale(157)

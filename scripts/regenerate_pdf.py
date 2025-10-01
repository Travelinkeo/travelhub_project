
import os
import django
import sys

# --- Django Setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()
# --- End Django Setup ---

from core.services.pdf_service import generar_pdf_voucher_unificado
from core.models import Venta

# El ID de la venta que creamos en los pasos anteriores
VENTA_ID = 12

def run():
    print(f"Regenerando PDF para Venta ID: {VENTA_ID} con la nueva plantilla...")
    
    try:
        # Verificamos que la venta exista
        Venta.objects.get(pk=VENTA_ID)

        pdf_bytes, filename = generar_pdf_voucher_unificado(venta_id=VENTA_ID)

        if pdf_bytes and filename:
            output_dir = 'media/boletos_generados'
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)
            
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
            
            print("-" * 50)
            print("¡PDF REGENERADO CON ÉXITO!")
            print(f"El nuevo voucher ha sido guardado en: {os.path.abspath(output_path)}")
            print("-" * 50)
        else:
            raise Exception("La función de generación de PDF no devolvió un archivo.")

    except Venta.DoesNotExist:
        print(f"\n*** ERROR: No se encontró la Venta con ID {VENTA_ID}. ***")
    except Exception as e:
        print(f"\n*** Ocurrió un error durante la regeneración: {e} ***")

if __name__ == "__main__":
    run()

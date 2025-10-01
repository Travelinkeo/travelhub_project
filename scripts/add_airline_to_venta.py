import os
import django
import sys

# --- Django Setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()
# --- End Django Setup ---

from core.models import Venta

VENTA_ID = 12
AIRLINE_NAME = 'WINGO'

def run():
    print(f"Actualizando Venta ID: {VENTA_ID} para asegurar el nombre de la aerolínea...")
    try:
        venta = Venta.objects.get(pk=VENTA_ID)
        venta.descripcion_general = AIRLINE_NAME
        venta.save(update_fields=['descripcion_general'])
        print(f"Venta {VENTA_ID} actualizada con el nombre de la aerolínea: {AIRLINE_NAME}")
    except Venta.DoesNotExist:
        print(f"ERROR: No se encontró la Venta con ID {VENTA_ID}.")
    except Exception as e:
        print(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    run()
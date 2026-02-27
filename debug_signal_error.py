import os
import django
import traceback
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado
from core.signals import crear_o_actualizar_venta_desde_boleto

def debug_signal(pk):
    print(f"--- DEBUGGING SIGNAL FOR BOLETO {pk} ---")
    try:
        instance = BoletoImportado.objects.get(pk=pk)
        if not instance.datos_parseados:
            print("No hay datos parseados para este boleto.")
            return

        # Simular la señal manualmente
        print("Llamando a crear_o_actualizar_venta_desde_boleto manualmente...")
        try:
            crear_o_actualizar_venta_desde_boleto(
                sender=BoletoImportado,
                instance=instance,
                created=False
            )
            print("Señal ejecutada con éxito (sorprendente si fallaba antes)")
        except Exception as e:
            print(f"\n!!! EXCEPCION EN SEÑAL: {type(e).__name__}: {e}")
            traceback.print_exc()
            
            # Si falló, vamos a ver qué campo pudo ser
            if 'varying(150)' in str(e):
                print("\nAnalizando datos que la señal usa:")
                data = instance.datos_parseados.get('normalized', instance.datos_parseados)
                p_name = data.get('passenger_name') or data.get('NOMBRE_DEL_PASAJERO') or ''
                aerolinea = data.get('airline_name') or data.get('NOMBRE_AEROLINEA') or 'N/A'
                print(f"Pasajero (raw): '{p_name}' (len: {len(p_name)})")
                print(f"Aerolínea (raw): '{aerolinea}' (len: {len(aerolinea)})")

    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    id_test = int(sys.argv[1]) if len(sys.argv) > 1 else 1005
    debug_signal(id_test)

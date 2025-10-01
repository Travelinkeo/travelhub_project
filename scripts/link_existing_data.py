
import os
import django
import sys

# --- Django Setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()
# --- End Django Setup ---

from django.db import transaction
from core.models import Venta
from core.models.boletos import BoletoImportado

# --- Datos de las ventas y PDFs que ya existen ---
VENTAS_A_CONECTAR = [
    {
        "venta_id": 12,
        "localizador": "MSYHMI",
        "pdf_filename": "Voucher-MSYHMI.pdf",
        "original_file": "OTRA CARPETA/MSYHMI.pdf" # Archivo original que empezamos a procesar
    },
    {
        "venta_id": 14,
        "localizador": "MSYHMI-2",
        "pdf_filename": "Voucher-MSYHMI-2.pdf",
        "original_file": "OTRA CARPETA/MSYHMI.pdf" # El origen es el mismo
    }
]

def run():
    print("Iniciando script para enlazar Ventas existentes con Boletos Importados...")
    
    with transaction.atomic():
        for data in VENTAS_A_CONECTAR:
            venta_id = data['venta_id']
            localizador = data['localizador']
            
            print(f"Procesando Venta ID: {venta_id} con Localizador: {localizador}")

            try:
                venta = Venta.objects.get(pk=venta_id)
                
                # Usamos get_or_create para no duplicar si el script se corre varias veces
                boleto_importado, created = BoletoImportado.objects.get_or_create(
                    venta_asociada=venta,
                    defaults={
                        'localizador_pnr': localizador,
                        'estado_parseo': BoletoImportado.EstadoParseo.COMPLETADO,
                        # Asignamos el archivo original de donde vino todo
                        'archivo_boleto': data['original_file']
                    }
                )

                if created:
                    print(f"- Creado nuevo registro BoletoImportado (ID: {boleto_importado.id_boleto_importado}).")
                else:
                    print(f"- Encontrado registro BoletoImportado existente (ID: {boleto_importado.id_boleto_importado}).")

                # Asignamos la ruta del PDF generado al campo correcto
                pdf_path = os.path.join('boletos_generados', '2025', '09', data['pdf_filename'])
                boleto_importado.archivo_pdf_generado.name = pdf_path
                
                # Guardamos la instancia de BoletoImportado
                boleto_importado.save(update_fields=['archivo_pdf_generado'])
                print(f"- PDF generado ({pdf_path}) enlazado correctamente.")

            except Venta.DoesNotExist:
                print(f"- *** ERROR: No se encontró la Venta con ID {venta_id}. Saltando...")
            except Exception as e:
                print(f"- *** Ocurrió un error inesperado: {e} ***")
                # La transacción se revierte si hay un error
                raise

    print("\nProceso de enlazado de datos completado.")

if __name__ == "__main__":
    run()

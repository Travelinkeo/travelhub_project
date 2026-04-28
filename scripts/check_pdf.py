
import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from apps.bookings.models import BoletoImportado

try:
    boleto_id = 959
    boleto = BoletoImportado.objects.get(pk=boleto_id)
    print(f"Boleto ID: {boleto_id}")
    print(f"Estado Parseo: {boleto.estado_parseo}")
    print(f"Archivo PDF Generado: {boleto.archivo_pdf_generado}")
    if boleto.archivo_pdf_generado:
        print(f"PDF Path: {boleto.archivo_pdf_generado.path}")
        print(f"Exists on disk? {os.path.exists(boleto.archivo_pdf_generado.path)}")
    else:
        print("No PDF generated.")
        
    print(f"Datos Parseados Keys: {boleto.datos_parseados.keys() if boleto.datos_parseados else 'None'}")
    
except BoletoImportado.DoesNotExist:
    print(f"Boleto {boleto_id} no encontrado.")
except Exception as e:
    print(f"Error checking boleto: {e}")

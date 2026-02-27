import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado
from core.services.ticket_parser_service import TicketParserService

pks = [1049, 1050]

for pk in pks:
    print(f"\n{'='*40}")
    print(f"REVISANDO REGISTRO {pk}")
    print(f"{'='*40}")
    
    boleto = BoletoImportado.objects.filter(pk=pk).first()
    if not boleto:
        print(f"❌ Boleto {pk} no encontrado en la base de datos.")
        continue
    
    print(f"Archivo asociado: {boleto.archivo_boleto.name if boleto.archivo_boleto else 'N/A'}")
    print(f"Estado actual: {boleto.estado_parseo}")
    print(f"Log de Parseo actual:\n{boleto.log_parseo}")
    
    print("\n[+] INTENTANDO RE-PROCESAR...")
    try:
        service = TicketParserService()
        result = service._ejecutar_procesamiento_base(pk)
        
        boleto.refresh_from_db()
        print(f"\n[OK] RE-PROCESO COMPLETADO")
        print(f"Nuevo Estado: {boleto.estado_parseo}")
        print(f"Nuevo Log:\n{boleto.log_parseo}")
        print(f"Resultado devuelto por el servicio: {type(result)}")
        
    except Exception as e:
        import traceback
        print(f"\n[!] CRASH DURANTE RE-PROCESO: {e}")
        traceback.print_exc()


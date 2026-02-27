import os
import django
import traceback
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado
from core.services.ticket_parser_service import TicketParserService
from django.db.models.signals import post_save

# Desconectar señales para evitar Celery y ruido
from core.signals import crear_o_actualizar_venta_desde_boleto
# post_save.disconnect(crear_o_actualizar_venta_desde_boleto, sender='bookings.BoletoImportado')

def debug_error(pk):
    print(f"--- DEBUGGING BOLETO {pk} (Synchronous, Signals Disabled) ---")
    try:
        b = BoletoImportado.objects.get(pk=pk)
        b.estado_parseo = 'PEN'
        b.localizador_pnr = None
        b.save() # Esto disparaba la señal antes, ahora no.
        
        service = TicketParserService()
        
        # Simular el proceso que falla
        try:
            print("Llamando a service.procesar_boleto(pk)...")
            # El service ya tiene un try/except que guarda el error en b.log_parseo
            service.procesar_boleto(pk)
            
            b.refresh_from_db()
            print(f"Estado final en DB: {b.estado_parseo}")
            if b.estado_parseo == 'ERR':
                print(f"Log de error: {b.log_parseo}")
            
            # Inspección manual si falló con DataError
            if 'DataError' in (b.log_parseo or ''):
                print("\n!!! Detectado DataError en el log. Analizando campos en memoria...")
                for field in b._meta.fields:
                    if hasattr(field, 'max_length') and field.max_length:
                        val = getattr(b, field.name)
                        if val:
                             s_val = str(val)
                             print(f"[{field.name}] Limit: {field.max_length} | Real: {len(s_val)} | Value: {s_val[:50]}...")
                             if len(s_val) > field.max_length:
                                 print(f"   >>> EXCEDIDO! <<<")

        except Exception as e:
            print(f"Excepción EXTERNA: {e}")
            traceback.print_exc()

    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    id_test = int(sys.argv[1]) if len(sys.argv) > 1 else 1005
    debug_error(id_test)

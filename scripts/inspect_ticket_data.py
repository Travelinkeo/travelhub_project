
import os
import django
import sys
import json

def inspect_ticket(ticket_id):
    from apps.bookings.models import BoletoImportado
    
    try:
        t = BoletoImportado.objects.get(pk=ticket_id)
        print(f"--- Datos Boleto ID {ticket_id} ---")
        print(f"Formato Detectado: {t.formato_detectado}")
        print(f"Estado Parseo: {t.estado_parseo}")
        print(f"Agencia: {t.agencia}")
        
        parsed = t.datos_parseados
        if parsed:
            print("\n--- JSON Parseado ---")
            print(json.dumps(parsed, indent=2, ensure_ascii=False))
        else:
            print("\n❌ No hay datos parseados (JSON vacío).")
            
    except BoletoImportado.DoesNotExist:
        print(f"❌ Boleto ID {ticket_id} no existe.")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.append(project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
    django.setup()
    
    inspect_ticket(95) # Usamos el ID más reciente que vimos en los logs (aunque probare el ultimo real)
    # Mejor buscamos el ultimo
    from apps.bookings.models import BoletoImportado
    last = BoletoImportado.objects.last()
    if last:
        inspect_ticket(last.pk)

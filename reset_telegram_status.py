
import os
import django
import sys

# Setup Django Environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import BoletoImportado

def reset_telegram_for_testing():
    print("--- RESETEANDO ESTADO DE TELEGRAM PARA AVIOR ---")
    
    # Buscar boletos recientes de Avior (Prefijo 742 o aerolínea AVIOR)
    # También incluimos el ticket específico que falló si lo encontramos
    tickets = BoletoImportado.objects.filter(
        archivo_boleto__icontains='Avior'
    ).order_by('-fecha_subida')[:5]
    
    # Or just get the very last ones regardless of name, to be safe
    last_tickets = BoletoImportado.objects.all().order_by('-fecha_subida')[:5]
    
    unique_tickets = list(set(list(tickets) + list(last_tickets)))
    
    count = 0
    for b in unique_tickets:
        if b.telegram_file_id:
            print(f"🔄 Limpiando estado Telegram para Boleto #{b.numero_boleto} (ID: {b.pk}) - Estado previo: {b.telegram_file_id}")
            b.telegram_file_id = None 
            b.save(update_fields=['telegram_file_id'])
            count += 1
        else:
            print(f"ℹ️ Boleto #{b.numero_boleto} (ID: {b.pk}) ya estaba limpio.")

    print(f"\n✅ Total reseteados: {count}")
    print("Ahora al reprocesar, el sistema intentará enviar la notificación nuevamente.")

if __name__ == '__main__':
    reset_telegram_for_testing()

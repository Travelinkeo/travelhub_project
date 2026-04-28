
import os
import django
import sys
from django.utils import timezone
from datetime import timedelta

def check_recent_tickets():
    from apps.bookings.models import BoletoImportado
    
    print("--- Buscando Boletos Recientes (Últimas 48 horas) ---")
    
    # Check last 48h
    time_threshold = timezone.now() - timedelta(hours=48)
    recent_tickets = BoletoImportado.objects.filter(fecha_subida__gte=time_threshold).order_by('-fecha_subida')
    
    count = recent_tickets.count()
    print(f"Total encontrados: {count}")
    
    for t in recent_tickets:
        print(f"[{t.fecha_subida.strftime('%Y-%m-%d %H:%M')}] ID: {t.pk} - Estado: {t.estado_parseo}")
        print(f"   Archivo: {t.archivo_boleto.name if t.archivo_boleto else 'Sin PDF'}")
        
    print("\n--- Estado General ---")
    print(f"Total Boletos en DB: {BoletoImportado.objects.count()}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.append(project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
    django.setup()
    
    check_recent_tickets()

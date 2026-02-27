
import os
import django
import sys

def manual_scan():
    print("--- Iniciando Escaneo Manual de Correo ---")
    from core.services.email_monitor_service import EmailMonitorService
    
    from core.models import Agencia
    try:
        agencia = Agencia.objects.first() # Usamos la primera encontrada (Travelinkeo)
        print(f"Usando agencia: {agencia}")
        
        monitor = EmailMonitorService(
            agencia=agencia,
            notification_type='telegram', 
            process_all=True  # IMPORTANTE: Forzar revisión de correos ya leídos
        )
        print("Monitor inicializado. Conectando a Gmail...")
        
        # Forzamos una revisión de correos recibidos
        count = monitor.procesar_una_vez()
        
        print(f"✅ Escaneo completo. Procesados: {count}")
    except Exception as e:
        print(f"❌ Error durante el escaneo: {e}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.append(project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
    django.setup()
    
    manual_scan()

"""
Script de prueba para notificación WhatsApp de boletos
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.services.email_monitor_service import EmailMonitorService

def main():
    print("=" * 80)
    print("TEST: Monitoreo de Boletos con WhatsApp")
    print("=" * 80)
    print()
    print("Destino: +584126080861")
    print("Procesando solo correos NO LEÍDOS...")
    print()
    
    monitor = EmailMonitorService(
        notification_type='whatsapp',
        destination='+584126080861',
        mark_as_read=True,
        process_all=False,
        force_reprocess=False
    )
    
    procesados = monitor.procesar_una_vez()
    
    print()
    print("=" * 80)
    print(f"RESULTADO: {procesados} boletos procesados")
    print("=" * 80)

if __name__ == '__main__':
    main()

"""
Script de migración para usar el monitor unificado
Depreca: email_monitor.py, email_monitor_v2.py, email_monitor_whatsapp_drive.py
"""
import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
import django
django.setup()

from core.services.email_monitor_service import EmailMonitorService

def main():
    print("=" * 60)
    print("MIGRACIÓN A MONITOR UNIFICADO")
    print("=" * 60)
    
    print("\n✅ Monitor unificado disponible en:")
    print("   core/services/email_monitor_service.py")
    
    print("\n📝 Uso:")
    print("""
    # WhatsApp
    monitor = EmailMonitorService(
        notification_type='whatsapp',
        destination='+584121234567',
        interval=60,
        mark_as_read=False
    )
    monitor.start()
    
    # Email
    monitor = EmailMonitorService(
        notification_type='email',
        destination='admin@example.com',
        interval=60
    )
    monitor.start()
    
    # WhatsApp + Google Drive
    monitor = EmailMonitorService(
        notification_type='whatsapp_drive',
        destination='+584121234567',
        interval=60
    )
    monitor.start()
    """)
    
    print("\n⚠️  Archivos deprecados (mover a scripts_archive/):")
    print("   - core/email_monitor.py")
    print("   - core/email_monitor_v2.py")
    print("   - core/email_monitor_whatsapp_drive.py")
    
    print("\n✅ Migración completada")

if __name__ == '__main__':
    main()

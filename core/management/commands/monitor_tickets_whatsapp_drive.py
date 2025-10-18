from django.core.management.base import BaseCommand
from core.services.email_monitor_service import EmailMonitorService

class Command(BaseCommand):
    help = 'Monitorea correos y envia por WhatsApp con link de Google Drive'

    def add_arguments(self, parser):
        parser.add_argument('--phone', type=str, required=True, help='Numero WhatsApp')
        parser.add_argument('--interval', type=int, default=60, help='Intervalo en segundos')
        parser.add_argument('--mark-read', action='store_true', help='Marcar como leidos')

    def handle(self, *args, **options):
        self.stdout.write(f"Iniciando monitor -> WhatsApp {options['phone']}")
        self.stdout.write("PDFs se subiran a Google Drive")
        
        monitor = EmailMonitorService(
            notification_type='whatsapp_drive',
            destination=options['phone'],
            interval=options['interval'],
            mark_as_read=options['mark_read']
        )
        
        try:
            monitor.start()
        except KeyboardInterrupt:
            self.stdout.write('Monitor detenido')

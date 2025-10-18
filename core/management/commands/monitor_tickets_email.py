from django.core.management.base import BaseCommand
from core.services.email_monitor_service import EmailMonitorService

class Command(BaseCommand):
    help = 'Monitorea correos de boletos y envia por email'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=True, help='Email destino')
        parser.add_argument('--interval', type=int, default=60, help='Intervalo en segundos')
        parser.add_argument('--mark-read', action='store_true', help='Marcar como leidos')

    def handle(self, *args, **options):
        self.stdout.write(f"Iniciando monitor -> {options['email']}")
        
        monitor = EmailMonitorService(
            notification_type='email',
            destination=options['email'],
            interval=options['interval'],
            mark_as_read=options['mark_read']
        )
        
        try:
            monitor.start()
        except KeyboardInterrupt:
            self.stdout.write('Monitor detenido')

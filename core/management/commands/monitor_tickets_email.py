from django.core.management.base import BaseCommand
from core.services.email_monitor_service import EmailMonitorService

class Command(BaseCommand):
    help = 'Monitorea correos de boletos y envia por email'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=True, help='Email destino')
        parser.add_argument('--interval', type=int, default=60, help='Intervalo en segundos')
        parser.add_argument('--mark-read', action='store_true', help='Marcar como leidos')
        parser.add_argument('--once', action='store_true', help='Procesar una sola vez y salir')
        parser.add_argument('--all', action='store_true', help='Procesar todos los correos (incluso leidos)')
        parser.add_argument('--force', action='store_true', help='Reprocesar boletos existentes')

    def handle(self, *args, **options):
        self.stdout.write(f"Iniciando monitor -> {options['email']}")
        
        monitor = EmailMonitorService(
            notification_type='email',
            destination=options['email'],
            interval=options['interval'],
            mark_as_read=options['mark_read'],
            process_all=options.get('all', False),
            force_reprocess=options.get('force', False)
        )
        
        try:
            if options['once']:
                # Procesar una sola vez
                count = monitor.procesar_una_vez()
                self.stdout.write(self.style.SUCCESS(f'✅ Procesados {count} correos'))
            else:
                # Modo continuo
                monitor.start()
        except KeyboardInterrupt:
            self.stdout.write('Monitor detenido')

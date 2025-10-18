"""
Comando para monitorear correos de boletos y enviar por WhatsApp
"""
from django.core.management.base import BaseCommand
from core.services.email_monitor_service import EmailMonitorService


class Command(BaseCommand):
    help = 'Monitorea correos de boletos (KIU/SABRE) y envía por WhatsApp'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            required=True,
            help='Número WhatsApp destino (ej: +584121234567)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Intervalo de chequeo en segundos (default: 60)'
        )
        parser.add_argument(
            '--mark-read',
            action='store_true',
            help='Marcar correos como leídos después de procesar'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                f"Iniciando monitor de boletos -> {options['phone']}"
            )
        )
        
        monitor = EmailMonitorService(
            notification_type='whatsapp',
            destination=options['phone'],
            interval=options['interval'],
            mark_as_read=options['mark_read']
        )
        
        try:
            monitor.start()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nMonitor detenido por el usuario'))

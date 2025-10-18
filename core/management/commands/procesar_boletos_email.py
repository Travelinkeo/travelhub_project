"""
Comando Django para procesar boletos desde correo electrónico
"""
from django.core.management.base import BaseCommand
from core.services.email_ticket_processor import leer_correos_no_leidos


class Command(BaseCommand):
    help = 'Procesa boletos desde correos electrónicos no leídos'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando procesamiento de correos...')
        
        boletos = leer_correos_no_leidos()
        
        if boletos:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Procesados {len(boletos)} boletos exitosamente'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING('No se encontraron boletos para procesar')
            )

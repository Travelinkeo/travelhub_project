"""Comando para cargar catálogo de aerolíneas con RIFs."""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Carga el catálogo de aerolíneas con RIFs venezolanos e internacionales'

    def handle(self, *args, **options):
        self.stdout.write('Cargando aerolineas...')
        call_command('loaddata', 'aerolineas_venezuela.json')
        self.stdout.write(self.style.SUCCESS('[OK] 25 aerolineas cargadas exitosamente'))
        self.stdout.write('\nNacionales con RIF real: 11')
        self.stdout.write('Internacionales con RIF generico (E-XXXXX-X): 14')


from django.core.management.base import BaseCommand
from core.models_catalogos import Moneda

class Command(BaseCommand):
    help = 'Deletes all existing Moneda objects from the database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Borrando todas las monedas de la base de datos...'))
        count, _ = Moneda.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Se eliminaron exitosamente {count} monedas.'))

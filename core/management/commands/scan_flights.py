
from django.core.management.base import BaseCommand
from core.tasks import check_upcoming_flights

class Command(BaseCommand):
    help = 'Ejecuta manualmente el chequeo de vuelos próximos'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando chequeo de vuelos...")
        res = check_upcoming_flights()
        self.stdout.write(self.style.SUCCESS(f"Resultado: {res}"))

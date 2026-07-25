from django.core.management.base import BaseCommand

from apps.common.models import Moneda


class Command(BaseCommand):
    """Comando de gestión personalizado."""
    help = "Deletes all existing Moneda objects from the database"

    def handle(self, *args, **options):
        """Método: handle."""
        self.stdout.write(self.style.WARNING("Borrando todas las monedas de la base de datos..."))
        count, _ = Moneda.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"Se eliminaron exitosamente {count} monedas."))

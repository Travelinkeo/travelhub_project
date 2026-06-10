from django.core.management.base import BaseCommand
from django.db import transaction

from apps.crm.models import Cliente, Pasajero

CHUNK_SIZE = 500


class Command(BaseCommand):
    help = "Migrates historical clear-text passenger documents to the new encrypted format"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting passenger document encryption migration..."))

        p_count = 0
        for p in Pasajero.objects.all().iterator(chunk_size=CHUNK_SIZE):
            with transaction.atomic():
                p.save()
                p_count += 1
            if p_count % 5000 == 0:
                self.stdout.write(f"  Procesados {p_count} pasajeros...")

        c_count = 0
        for c in Cliente.objects.all().iterator(chunk_size=CHUNK_SIZE):
            with transaction.atomic():
                c.save()
                c_count += 1
            if c_count % 5000 == 0:
                self.stdout.write(f"  Procesados {c_count} clientes...")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully re-saved {p_count} passengers and {c_count} clients.")
        )
        self.stdout.write(
            self.style.NOTICE("Encryption is handled automatically by the model field on save.")
        )

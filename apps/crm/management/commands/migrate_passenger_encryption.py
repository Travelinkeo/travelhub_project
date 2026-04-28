from django.core.management.base import BaseCommand
from apps.crm.models import Pasajero, Cliente
from django.db import transaction

class Command(BaseCommand):
    help = 'Migrates historical clear-text passenger documents to the new encrypted format'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting passenger document encryption migration...'))
        
        with transaction.atomic():
            # Migrate Pasajeros
            pasajeros = Pasajero.objects.all()
            p_count = 0
            for p in pasajeros:
                # El guardado gatilla la encriptación automáticamente gracias al EncryptedCharField
                p.save()
                p_count += 1
            
            # Migrate Clientes
            clientes = Cliente.objects.all()
            c_count = 0
            for c in clientes:
                c.save()
                c_count += 1
                
        self.stdout.write(self.style.SUCCESS(f'Successfully re-saved {p_count} passengers and {c_count} clients.'))
        self.stdout.write(self.style.NOTICE('Encryption is handled automatically by the model field on save.'))

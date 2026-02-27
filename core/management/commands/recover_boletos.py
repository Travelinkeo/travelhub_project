
import os
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from apps.bookings.models import BoletoImportado, Venta
from core.services.ticket_parser_service import TicketParserService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Recover BoletoImportado records from media folder and link to existing Ventas'

    def handle(self, *args, **options):
        media_root = settings.MEDIA_ROOT
        boletos_dir = os.path.join(media_root, 'boletos_importados')
        
        if not os.path.exists(boletos_dir):
            self.stdout.write(self.style.ERROR(f"Directory not found: {boletos_dir}"))
            return

        self.stdout.write(f"Scanning {boletos_dir}...")
        
        restored = 0
        relinked = 0
        errors = 0
        skipped = 0

        # Walk through the directory (year/month structure)
        for root, dirs, files in os.walk(boletos_dir):
            for filename in files:
                file_path = os.path.join(root, filename)
                
                # Get relative path for database storage (e.g., boletos_importados/2024/05/ticket.pdf)
                # Django's FileField stores the path relative to MEDIA_ROOT
                rel_path = os.path.relpath(file_path, media_root).replace('\\', '/')
                
                # Check if record already exists
                boleto = BoletoImportado.objects.filter(archivo_boleto=rel_path).first()
                created = False

                if boleto:
                    if boleto.estado_parseo not in ['PEN', 'ERR']:
                         skipped += 1
                         continue
                    else:
                        self.stdout.write(f"Retry existing record: {filename}")
                else:
                    # 1. Create BoletoImportado
                    # We utilize the file name to guess the date or use file modification time
                    timestamp = os.path.getmtime(file_path)
                    file_date = datetime.fromtimestamp(timestamp)
                    
                    boleto = BoletoImportado(
                        archivo_boleto=rel_path,
                        fecha_subida=file_date,
                        estado_parseo=BoletoImportado.EstadoParseo.PENDIENTE
                    )
                    boleto.save()
                    created = True
                    restored += 1
                    self.stdout.write(f"Created record for: {filename}")

                # 2. Parse and Link using TicketParserService
                try:
                    parser = TicketParserService()
                    # procesar_boleto handles parsing, model updating, and idempotent Venta linking
                    venta = parser.procesar_boleto(boleto.pk) 
                    
                    if venta:
                        relinked += 1
                        self.stdout.write(self.style.SUCCESS(f"  -> Linked to Venta {venta.localizador} (ID: {venta.pk})"))
                    else:
                            self.stdout.write(self.style.WARNING(f"  -> Processed but no Venta returned/created."))

                except Exception as e:
                    logger.error(f"Error parsing/linking {filename}: {e}")
                    # Don't fail the recovery, just log
                    pass

                # End of file processing loop iteration

        self.stdout.write(self.style.SUCCESS(
            f"\nRecovery Complete:\n"
            f"- Restored: {restored}\n"
            f"- Relinked: {relinked}\n"
            f"- Skipped (Already existed): {skipped}\n"
            f"- Errors: {errors}"
        ))

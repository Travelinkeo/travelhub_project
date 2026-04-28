from django.core.management.base import BaseCommand
from core.models import TarifarioProveedor
from core.services.hotel_parser_service import HotelParserService

class Command(BaseCommand):
    help = 'Procesa un Tarifario de Proveedor usando Gemini Vision'

    def add_arguments(self, parser):
        parser.add_argument('tarifario_id', type=int, help='ID del TarifarioProveedor a procesar')

    def handle(self, *args, **options):
        tarifario_id = options['tarifario_id']
        try:
            tarifario = TarifarioProveedor.objects.get(pk=tarifario_id)
            self.stdout.write(f"Procesando tarifario: {tarifario} (PDF: {tarifario.archivo_pdf.name})...")
            
            service = HotelParserService(tarifario_id)
            if service.procesar_tarifario():
                self.stdout.write(self.style.SUCCESS(f"Tarifario {tarifario_id} procesado exitosamente."))
            else:
                self.stdout.write(self.style.ERROR(f"Error procesando tarifario {tarifario_id}."))
                
        except TarifarioProveedor.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Tarifario ID {tarifario_id} no encontrado."))

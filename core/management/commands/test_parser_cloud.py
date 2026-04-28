from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import Agencia
from apps.bookings.models import BoletoImportado
from core.services.ticket_parser_service import TicketParserService
import requests # Necesario para descargar de la nube
from io import BytesIO
import os

class Command(BaseCommand):
    help = 'Prueba forense compatible con Cloudinary'

    def add_arguments(self, parser):
        parser.add_argument('url_o_ruta', type=str, help='URL de Cloudinary o ruta local')

    def handle(self, *args, **options):
        ruta = options['url_o_ruta']
        self.stdout.write(f"☁️ 1. Analizando origen: {ruta}")

        archivo_contenido = None
        nombre_archivo = "test_cloud.pdf"

        # 1. DESCARGAR SI ES URL (CLOUDINARY)
        if ruta.startswith('http'):
            self.stdout.write("   - Detectado enlace web. Descargando...")
            try:
                response = requests.get(ruta)
                if response.status_code == 200:
                    archivo_contenido = response.content
                    self.stdout.write(self.style.SUCCESS("   - ✅ Archivo descargado a memoria ram."))
                else:
                    self.stdout.write(self.style.ERROR(f"   - ❌ Error descargando: {response.status_code}"))
                    return
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   - ❌ Error de conexión: {e}"))
                return
        # 2. LEER SI ES LOCAL
        else:
            if os.path.exists(ruta):
                with open(ruta, 'rb') as f:
                    archivo_contenido = f.read()
            else:
                self.stdout.write(self.style.ERROR("❌ Archivo local no encontrado."))
                return

        # 3. CREAR BOLETO FALSO
        agencia = Agencia.objects.first()
        archivo_simulado = SimpleUploadedFile(name=nombre_archivo, content=archivo_contenido)
        
        boleto = BoletoImportado.objects.create(
            archivo_boleto=archivo_simulado,
            agencia=agencia,
            estado_parseo='PEN'
        )
        self.stdout.write(self.style.SUCCESS(f"✅ 2. Boleto guardado en BD (ID: {boleto.id})"))

        # 4. EJECUTAR EL PARSER REAL
        self.stdout.write("⚙️ 3. Ejecutando Parser...")
        try:
            servicio = TicketParserService()
            # El servicio internamente debe ser capaz de manejar esto.
            # Si falla aquí, es que el servicio necesita el parche de abajo.
            venta = servicio.procesar_boleto(boleto.id)
            
            if venta:
                self.stdout.write(self.style.SUCCESS(f"🎉 ¡ÉXITO! Venta: {venta.total_venta} {venta.moneda_operacion}"))
            else:
                self.stdout.write(self.style.ERROR("💀 Falló: No se creó la venta."))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"💥 Error en el código del Parser: {e}"))
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models_catalogos import Moneda, TipoCambio
from core.bcv_scraper import obtener_tasas_bcv
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Actualiza las tasas de cambio desde el BCV (USD, EUR)'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando actualización de tasas BCV...")
        
        tasas = obtener_tasas_bcv()
        
        if not tasas:
            self.stderr.write(self.style.ERROR("No se obtuvieron tasas del BCV. Abortando."))
            return

        # Asegurar moneda base VES
        moneda_local, _ = Moneda.objects.get_or_create(
            codigo_iso='VES',
            defaults={'nombre': 'Bolívar Digital', 'simbolo': 'Bs.', 'es_moneda_local': True}
        )
        
        fecha_actual = timezone.now().date()
        
        for iso, tasa in tasas.items():
            if iso not in ['USD', 'EUR']: # Por ahora nos interesan estas
                continue
                
            moneda_origen, created = Moneda.objects.get_or_create(
                codigo_iso=iso,
                defaults={'nombre': f'Moneda {iso}', 'simbolo': iso}
            )
            
            # Crear o actualizar TipoCambio
            # Conversion: 1 USD = X VES -> Tasa BCV
            # En nuestro modelo TipoCambio: moneda_origen=USD, moneda_destino=VES, tasa=X
            
            tipo_cambio, created = TipoCambio.objects.update_or_create(
                moneda_origen=moneda_origen,
                moneda_destino=moneda_local,
                fecha_efectiva=fecha_actual,
                defaults={
                    'tasa_conversion': tasa
                }
            )
            
            action = "Creado" if created else "Actualizado"
            self.stdout.write(self.style.SUCCESS(f"{action} Tipo de Cambio: 1 {iso} = {tasa} VES ({fecha_actual})"))

        self.stdout.write(self.style.SUCCESS("Proceso completado."))

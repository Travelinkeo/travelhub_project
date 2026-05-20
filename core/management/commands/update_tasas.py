import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.finance.models.currencies import Moneda, TipoCambio
from apps.finance.services.bcv_scraper import obtener_tasas_bcv

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
            
            # 1. Actualizar TipoCambio (Estructura ERP)
            tipo_cambio, created_tc = TipoCambio.objects.update_or_create(
                moneda_origen=moneda_origen,
                moneda_destino=moneda_local,
                fecha_efectiva=fecha_actual,
                defaults={
                    'tasa_conversion': tasa
                }
            )

            # 2. Actualizar TasaCambio (Caché de UI/Header)
            from apps.finance.models.currencies import TasaCambio
            tasa_obj, created_tasa = TasaCambio.objects.update_or_create(
                fecha=fecha_actual,
                moneda=iso,
                defaults={'monto': tasa}
            )
            
            action = "Creado" if created_tc or created_tasa else "Actualizado"
            self.stdout.write(self.style.SUCCESS(f"{action} Tipo de Cambio: 1 {iso} = {tasa} VES ({fecha_actual})"))

        # Limpiar caché de la UI
        try:
            from django.core.cache import cache
            cache.delete('tasa_bcv_context')
            self.stdout.write(self.style.SUCCESS("Caché tasa_bcv_context eliminado."))
        except Exception as cache_err:
            self.stderr.write(self.style.WARNING(f"No se pudo limpiar caché: {cache_err}"))

        self.stdout.write(self.style.SUCCESS("Proceso completado."))

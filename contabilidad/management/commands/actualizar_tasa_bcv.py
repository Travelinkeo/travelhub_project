# contabilidad/management/commands/actualizar_tasa_bcv.py
"""
Comando para actualizar la tasa de cambio BCV.
Puede ejecutarse manualmente o programarse con cron/Task Scheduler.

Uso:
    python manage.py actualizar_tasa_bcv --tasa 45.50
    python manage.py actualizar_tasa_bcv --tasa 45.50 --fecha 2025-01-15
"""

import logging
from decimal import Decimal
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from contabilidad.models import TasaCambioBCV

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Actualiza o crea la tasa de cambio BCV para una fecha específica'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tasa',
            type=float,
            required=True,
            help='Tasa de cambio BSD/USD (ej: 45.50)'
        )
        parser.add_argument(
            '--fecha',
            type=str,
            help='Fecha en formato YYYY-MM-DD (default: hoy)'
        )
        parser.add_argument(
            '--fuente',
            type=str,
            default='Manual',
            help='Fuente de la tasa (default: Manual)'
        )

    def handle(self, *args, **options):
        try:
            tasa = Decimal(str(options['tasa']))
            
            if options['fecha']:
                fecha_tasa = date.fromisoformat(options['fecha'])
            else:
                fecha_tasa = timezone.now().date()
            
            fuente = options['fuente']
            
            if tasa <= 0:
                raise CommandError('La tasa debe ser mayor a cero')
            
            tasa_obj, created = TasaCambioBCV.objects.update_or_create(
                fecha=fecha_tasa,
                defaults={
                    'tasa_bsd_por_usd': tasa,
                    'fuente': fuente
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[OK] Tasa BCV creada: {fecha_tasa} = {tasa} BSD/USD'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[OK] Tasa BCV actualizada: {fecha_tasa} = {tasa} BSD/USD'
                    )
                )
            
            logger.info(f"Tasa BCV {'creada' if created else 'actualizada'}: {fecha_tasa} = {tasa}")
            
        except ValueError as e:
            raise CommandError(f'Error en formato de datos: {e}')
        except Exception as e:
            logger.error(f"Error actualizando tasa BCV: {e}")
            raise CommandError(f'Error: {e}')

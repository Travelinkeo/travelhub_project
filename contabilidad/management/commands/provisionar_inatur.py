# contabilidad/management/commands/provisionar_inatur.py
"""
Comando para provisionar la contribución mensual del 1% a INATUR.
Debe ejecutarse al final de cada mes.

Uso:
    python manage.py provisionar_inatur --mes 1 --anio 2025
    python manage.py provisionar_inatur  # Usa mes/año actual
"""

import logging
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from contabilidad.services import ContabilidadService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Provisiona la contribución del 1% a INATUR para un mes específico'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mes',
            type=int,
            help='Mes a procesar (1-12, default: mes actual)'
        )
        parser.add_argument(
            '--anio',
            type=int,
            help='Año a procesar (default: año actual)'
        )

    def handle(self, *args, **options):
        try:
            hoy = timezone.now().date()
            mes = options['mes'] or hoy.month
            anio = options['anio'] or hoy.year
            
            if not (1 <= mes <= 12):
                raise CommandError('El mes debe estar entre 1 y 12')
            
            if anio < 2000 or anio > 2100:
                raise CommandError('Año inválido')
            
            self.stdout.write(f'Provisionando INATUR para {mes}/{anio}...')
            
            asiento = ContabilidadService.provisionar_contribucion_inatur(mes, anio)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Provision INATUR completada\n'
                    f'  Asiento: {asiento.numero_asiento}\n'
                    f'  Total Debe: {asiento.total_debe} BSD\n'
                    f'  Total Haber: {asiento.total_haber} BSD'
                )
            )
            
        except Exception as e:
            logger.error(f"Error provisionando INATUR: {e}")
            raise CommandError(f'Error: {e}')

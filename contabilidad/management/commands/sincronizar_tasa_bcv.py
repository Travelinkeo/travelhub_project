# contabilidad/management/commands/sincronizar_tasa_bcv.py
"""
Comando para sincronizar automáticamente la tasa BCV desde su sitio web.
Puede ejecutarse manualmente o programarse con Task Scheduler.

Uso:
    python manage.py sincronizar_tasa_bcv
    python manage.py sincronizar_tasa_bcv --dry-run
"""

import logging
from django.core.management.base import BaseCommand

from contabilidad.bcv_client import BCVClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sincroniza la tasa de cambio BCV desde su sitio web oficial'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la sincronización sin guardar en DB'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write('Consultando tasa BCV...')
        
        tasa = BCVClient.obtener_tasa_actual()
        
        if tasa is None:
            self.stdout.write(
                self.style.ERROR('[ERROR] No se pudo obtener la tasa del BCV')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'[OK] Tasa obtenida: {tasa} BSD/USD')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('[DRY-RUN] No se guardó en base de datos')
            )
            return
        
        if BCVClient.actualizar_tasa_db(tasa, fuente="BCV Web (Auto)"):
            self.stdout.write(
                self.style.SUCCESS('[OK] Tasa guardada en base de datos')
            )
        else:
            self.stdout.write(
                self.style.ERROR('[ERROR] No se pudo guardar la tasa')
            )

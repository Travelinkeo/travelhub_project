# contabilidad/management/commands/sincronizar_tasa_bcv.py
"""
Comando mejorado para sincronizar tasas de cambio de Venezuela.
Obtiene: BCV oficial, Promedio, P2P y otras fuentes.

Uso:
    python manage.py sincronizar_tasa_bcv
    python manage.py sincronizar_tasa_bcv --dry-run
    python manage.py sincronizar_tasa_bcv --todas  # Muestra todas las tasas
"""

import logging
from django.core.management.base import BaseCommand
from datetime import datetime

from contabilidad.tasas_venezuela_client import TasasVenezuelaClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sincroniza tasas de cambio de Venezuela (BCV, Promedio, P2P)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la sincronización sin guardar en DB'
        )
        parser.add_argument(
            '--todas',
            action='store_true',
            help='Muestra todas las tasas disponibles'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        mostrar_todas = options['todas']
        
        self.stdout.write(self.style.HTTP_INFO('=' * 60))
        self.stdout.write(self.style.HTTP_INFO('  SINCRONIZACIÓN DE TASAS DE CAMBIO - VENEZUELA'))
        self.stdout.write(self.style.HTTP_INFO('=' * 60))
        self.stdout.write(f'Fecha/Hora: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write('')
        
        # Obtener todas las tasas
        self.stdout.write('Consultando tasas...')
        tasas = TasasVenezuelaClient.obtener_todas_tasas()
        
        if not tasas:
            self.stdout.write(
                self.style.ERROR('[ERROR] No se pudieron obtener las tasas')
            )
            return
        
        # Mostrar tasas principales
        self.stdout.write(self.style.SUCCESS(f'\n[OK] {len(tasas)} tasas obtenidas\n'))
        
        # BCV Oficial
        if 'oficial' in tasas:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  BCV OFICIAL:  {tasas['oficial']['price']:>10.2f} Bs/USD"
                )
            )
        
        # Paralelo
        if 'paralelo' in tasas:
            self.stdout.write(
                self.style.WARNING(
                    f"  PARALELO:     {tasas['paralelo']['price']:>10.2f} Bs/USD"
                )
            )
        
        # Bitcoin
        if 'bitcoin' in tasas:
            self.stdout.write(
                self.style.HTTP_INFO(
                    f"  BITCOIN:      {tasas['bitcoin']['price']:>10.2f} Bs/USD"
                )
            )
        
        # Mostrar todas si se solicita
        if mostrar_todas:
            self.stdout.write('\n' + '-' * 60)
            self.stdout.write('TODAS LAS TASAS DISPONIBLES:')
            self.stdout.write('-' * 60)
            for key, data in sorted(tasas.items()):
                nombre = data.get('title', key).ljust(25)
                precio = f"{data['price']:>10.2f}"
                self.stdout.write(f"  {nombre} {precio} Bs/USD")
        
        # Guardar en base de datos
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n[DRY-RUN] No se guardó en base de datos')
            )
        else:
            self.stdout.write('\nGuardando en base de datos...')
            resultados = TasasVenezuelaClient.actualizar_tasas_db()
            
            if resultados.get('oficial'):
                self.stdout.write(
                    self.style.SUCCESS('[OK] Tasa BCV guardada correctamente')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('[ERROR] No se pudo guardar la tasa BCV')
                )
        
        self.stdout.write(self.style.HTTP_INFO('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('Sincronización completada'))
        self.stdout.write(self.style.HTTP_INFO('=' * 60))

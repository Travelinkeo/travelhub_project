"""
Management command para sincronizar tasas automáticamente
Reemplaza el script .bat de Windows
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from contabilidad.management.commands.sincronizar_tasa_bcv import Command as SincronizarBCV
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sincroniza tasas de cambio automáticamente (BCV + otras fuentes)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--log-file',
            type=str,
            default='logs/tasas_sync.log',
            help='Archivo de log para sincronización'
        )

    def handle(self, *args, **options):
        log_file = options['log_file']
        
        # Configurar logging a archivo
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        self.stdout.write(f"[{timezone.now()}] Iniciando sincronización de tasas...")
        logger.info("Iniciando sincronización automática de tasas")
        
        try:
            # Ejecutar sincronización BCV
            bcv_command = SincronizarBCV()
            bcv_command.handle()
            
            self.stdout.write(self.style.SUCCESS('✅ Sincronización completada'))
            logger.info("Sincronización completada exitosamente")
            
        except Exception as e:
            error_msg = f"Error en sincronización: {str(e)}"
            self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))
            logger.error(error_msg, exc_info=True)
            raise

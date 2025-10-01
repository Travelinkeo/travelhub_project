"""
Comando para enviar recordatorios de pago automáticos
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Venta
from core.email_service import enviar_recordatorio_pago


class Command(BaseCommand):
    help = 'Envía recordatorios de pago para ventas pendientes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=3,
            help='Días desde la venta para enviar recordatorio (default: 3)'
        )

    def handle(self, *args, **options):
        dias = options['dias']
        fecha_limite = timezone.now() - timedelta(days=dias)
        
        # Buscar ventas pendientes de pago creadas hace X días
        ventas_pendientes = Venta.objects.filter(
            estado__in=['PEN', 'PAR'],
            fecha_venta__lte=fecha_limite,
            saldo_pendiente__gt=0,
            cliente__email__isnull=False
        ).exclude(cliente__email='')
        
        enviados = 0
        errores = 0
        
        for venta in ventas_pendientes:
            try:
                if enviar_recordatorio_pago(venta):
                    enviados += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Recordatorio enviado: {venta.localizador}')
                    )
                else:
                    errores += 1
            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(f'Error en {venta.localizador}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Proceso completado: {enviados} enviados, {errores} errores'
            )
        )
"""
Comando para enviar recordatorios de pago a ventas pendientes
Uso: python manage.py enviar_recordatorios_pago [--dias=3]
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Venta
from core.notification_service import notificar_recordatorio_pago


class Command(BaseCommand):
    help = 'Envía recordatorios de pago a ventas con saldo pendiente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=3,
            help='Días desde la última actualización para enviar recordatorio (default: 3)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula el envío sin enviar emails reales'
        )

    def handle(self, *args, **options):
        dias = options['dias']
        dry_run = options['dry_run']
        fecha_limite = timezone.now() - timedelta(days=dias)
        
        # Buscar ventas con saldo pendiente
        ventas_pendientes = Venta.objects.filter(
            estado__in=['PEN', 'PAR'],
            saldo_pendiente__gt=0,
            modificado__lte=fecha_limite,
            cliente__isnull=False,
            cliente__email__isnull=False
        ).exclude(cliente__email='')
        
        total = ventas_pendientes.count()
        enviados = 0
        
        self.stdout.write(f"Encontradas {total} ventas con pago pendiente")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("Modo DRY-RUN: No se enviarán emails"))
        
        for venta in ventas_pendientes:
            if dry_run:
                contacto = venta.cliente.email or venta.cliente.telefono or 'Sin contacto'
                self.stdout.write(f"  [DRY-RUN] Venta {venta.localizador} - {contacto}")
            else:
                resultados = notificar_recordatorio_pago(venta)
                if resultados['email'] or resultados['whatsapp']:
                    enviados += 1
                    canales = []
                    if resultados['email']:
                        canales.append(f"Email: {venta.cliente.email}")
                    if resultados['whatsapp']:
                        canales.append(f"WhatsApp: {venta.cliente.telefono}")
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ {venta.localizador} - {', '.join(canales)}")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ Error enviando a {venta.localizador}")
                    )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"\nTotal enviados: {enviados}/{total}")
            )

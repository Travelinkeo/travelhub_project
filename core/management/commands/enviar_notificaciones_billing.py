"""
Management command para enviar notificaciones automáticas de billing.
Ejecutar diariamente con cron/Task Scheduler.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models.agencia import Agencia
from core.services.billing_notifications import (
    enviar_email_trial_expirando,
    enviar_email_trial_expirado,
    enviar_email_limite_alcanzado
)


class Command(BaseCommand):
    help = 'Envía notificaciones automáticas de billing'

    def handle(self, *args, **options):
        hoy = timezone.now().date()
        
        # 1. Trials que expiran en 7 días
        en_7_dias = hoy + timedelta(days=7)
        trials_7_dias = Agencia.objects.filter(
            plan='FREE',
            fecha_fin_trial=en_7_dias,
            activa=True
        )
        
        for agencia in trials_7_dias:
            try:
                enviar_email_trial_expirando(agencia, 7)
                self.stdout.write(self.style.SUCCESS(
                    f'Email enviado a {agencia.nombre} (7 días)'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error: {e}'))
        
        # 2. Trials que expiran en 3 días
        en_3_dias = hoy + timedelta(days=3)
        trials_3_dias = Agencia.objects.filter(
            plan='FREE',
            fecha_fin_trial=en_3_dias,
            activa=True
        )
        
        for agencia in trials_3_dias:
            try:
                enviar_email_trial_expirando(agencia, 3)
                self.stdout.write(self.style.SUCCESS(
                    f'Email enviado a {agencia.nombre} (3 días)'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error: {e}'))
        
        # 3. Trials expirados hoy
        trials_expirados = Agencia.objects.filter(
            plan='FREE',
            fecha_fin_trial=hoy,
            activa=True
        )
        
        for agencia in trials_expirados:
            try:
                enviar_email_trial_expirado(agencia)
                self.stdout.write(self.style.SUCCESS(
                    f'Email de expiración enviado a {agencia.nombre}'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error: {e}'))
        
        # 4. Agencias que alcanzaron 90% del límite de ventas
        agencias_limite = Agencia.objects.filter(activa=True).exclude(plan='ENTERPRISE')
        
        for agencia in agencias_limite:
            porcentaje_uso = (agencia.ventas_mes_actual / agencia.limite_ventas_mes * 100) if agencia.limite_ventas_mes > 0 else 0
            
            if porcentaje_uso >= 90:
                try:
                    enviar_email_limite_alcanzado(agencia, 'ventas')
                    self.stdout.write(self.style.WARNING(
                        f'Alerta de límite enviada a {agencia.nombre} ({porcentaje_uso:.1f}%)'
                    ))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error: {e}'))
        
        self.stdout.write(self.style.SUCCESS('Notificaciones procesadas'))

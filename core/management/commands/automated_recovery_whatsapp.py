from django.core.management.base import BaseCommand

from apps.automation.services.collection_ai_service import CollectionAIService


class Command(BaseCommand):
    help = "Detecta agencias con pagos vencidos y envía mensajes de recuperación personalizados vía WhatsApp con IA."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula el proceso sin enviar mensajes reales.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        self.stdout.write(
            self.style.NOTICE(f"Iniciando proceso de recuperación financiera (Dry Run: {dry_run})")
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Modo simulación activado. No se enviarán mensajes.")
            )
            # In dry run, we just log who would be notified
            from django.utils import timezone

            from core.models.agencia import Agencia

            overdue = Agencia.objects.filter(activa=True, plan_status="past_due")
            expired_trials = Agencia.objects.filter(
                activa=True, plan="FREE", subscription_end_date__lt=timezone.now()
            )

            for ag in list(overdue) + list(expired_trials):
                self.stdout.write(
                    f"  - Se notificaría a: {ag.nombre} (WA: {ag.whatsapp or 'No configurado'})"
                )
        else:
            results = CollectionAIService.process_overdue_accounts()

            for res in results:
                status = (
                    self.style.SUCCESS("EXITO") if res.get("success") else self.style.ERROR("FALLO")
                )
                self.stdout.write(
                    f"Agencia: {res['agencia']} | Resultado: {status} | Error: {res.get('error', 'Ninguno')}"
                )

        self.stdout.write(self.style.SUCCESS("Proceso completado."))

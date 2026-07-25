import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Comando de gestión personalizado."""
    help = "Provisiona instancias de WhatsApp por agencia en Evolution API"

    def add_arguments(self, parser):
        """Método: add arguments."""
        parser.add_argument("--force", action="store_true", default=False)
        parser.add_argument("--slug", type=str, default=None)

    def handle(self, *args, **options):
        """Método: handle."""
        from apps.common.tasks import fetch_evolution_qr_task
        from apps.communications.services.evolution_api_service import EvolutionService
        from core.models.agencia import Agencia

        force = options["force"]
        only_slug = options["slug"]
        qs = (
            Agencia.objects.filter(activa=True)
            .select_related("configuracion")
            .filter(configuracion__subdominio_slug__isnull=False)
            .exclude(configuracion__subdominio_slug="")
        )
        if only_slug:
            qs = qs.filter(configuracion__subdominio_slug=only_slug)

        total = qs.count()
        self.stdout.write(f"Procesando {total} agencias...")
        creadas = 0
        ya_conectadas = 0
        errores = 0

        for ag in qs:
            slug = ag.subdominio_slug
            self.stdout.write(f"  Agencia: {ag.nombre} ({slug})")
            try:
                estado = EvolutionService.get_instance_state(slug)
                self.stdout.write(f"    Estado: {estado}")
                if estado == "open" and not force:
                    self.stdout.write(self.style.SUCCESS("    Ya conectada."))
                    ya_conectadas += 1
                    continue
                if estado in ("disconnected",) or force:
                    result = EvolutionService.create_instance(slug)
                    if result and isinstance(result, dict) and result.get("instance"):
                        self.stdout.write(self.style.SUCCESS(f"    Instancia creada: {slug}"))
                        fetch_evolution_qr_task.delay(slug)
                        creadas += 1
                    else:
                        self.stdout.write(self.style.WARNING(f"    Respuesta: {result}"))
                        errores += 1
                else:
                    self.stdout.write(f"    Estado {estado} - sin accion")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"    Error: {e}"))
                errores += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Resultado: {creadas} creadas, {ya_conectadas} ya conectadas, {errores} errores."
            )
        )

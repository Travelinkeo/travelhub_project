import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Comando de gestión personalizado."""
    help = "Ejecuta health checks de proveedores IA y claves API"

    def add_arguments(self, parser):
        """Método: add arguments."""
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ignorar el intervalo de 1 hora y forzar la ejecución",
        )

    def handle(self, *args, **options):
        """Método: handle."""
        from apps.automation.providerchain.health import get_health_summary, run_health_checks

        results = run_health_checks(force=options["force"])

        if not results:
            self.stdout.write("Health checks ya ejecutados recientemente. Usa --force para forzar.")
            return

        ok_count = sum(1 for r in results if r["status"] == "ok")
        fail_count = sum(1 for r in results if r["status"] == "fail")

        for r in results:
            if r["status"] == "ok":
                self.stdout.write(self.style.SUCCESS(f"  ✓ {r['type']}: {r['name']}"))
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ {r['type']}: {r['name']}"))

        self.stdout.write()
        self.stdout.write(self.style.SUCCESS(f"{ok_count} OK, {fail_count} FAIL"))

        summary = get_health_summary()
        secrets = summary["api_secrets"]
        self.stdout.write(
            f"Claves API: {secrets['ok']} ok, {secrets['fail']} fail, "
            f"{secrets['unknown']} sin probar"
        )

from django.core.management import call_command
from django.core.management.base import BaseCommand

from core.middleware import system_context


class Command(BaseCommand):
    """Comando de gestión personalizado."""
    help = "Setup completo de produccion: migrate, static, seed, cron keys"

    def handle(self, *args, **options):
        """Método: handle."""
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("TRAVELHUB - SETUP COMPLETO"))
        self.stdout.write("=" * 60)

        self.stdout.write("\n[1/5] Aplicando migraciones...")
        call_command("migrate", "--noinput", verbosity=1)
        self.stdout.write(self.style.SUCCESS("  Migraciones aplicadas."))

        self.stdout.write("\n[2/5] Generando archivos estaticos...")
        call_command("collectstatic", "--noinput", verbosity=0)
        self.stdout.write(self.style.SUCCESS("  Estaticos recolectados."))

        self.stdout.write("\n[3/5] Sembrando datos iniciales...")
        with system_context():
            call_command("seed_data", verbosity=0)
            call_command("seed_plan_contable", verbosity=0)
            call_command("setup_proveedores_vzla", verbosity=0)
            call_command("load_catalogs", verbosity=0)
        self.stdout.write(self.style.SUCCESS("  Datos iniciales sembrados."))

        self.stdout.write("\n[4/5] Creando CronApiKeys...")
        self._create_cron_keys()
        self.stdout.write(self.style.SUCCESS("  CronApiKeys creadas."))

        self.stdout.write("\n[5/5] Calentando cache...")
        try:
            call_command("warmup_cache", verbosity=0)
            self.stdout.write(self.style.SUCCESS("  Cache pre-calentado."))
        except Exception:
            self.stdout.write("  Cache skip (Redis no disponible).")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("SETUP COMPLETO - TravelHub listo."))
        self.stdout.write("=" * 60)

    def _create_cron_keys(self):
        """Método interna: create cron keys."""
        from core.models.cron_api_key import CronApiKey

        keys_config = [
            ("BCV Sync - Actualizacion diaria de tasas", 365),
            ("Payment Reminders - Recordatorios de pago", 90),
            ("Monthly Close - Cierre contable mensual", 90),
            ("Catalog Load - Carga de catalogos", 90),
        ]

        self.stdout.write("")
        self.stdout.write("  GUARDA ESTOS TOKENS AHORA. NO SE MOSTRARAN DE NUEVO.")
        self.stdout.write("  Usalos en cron-job.org como header X-Cron-Token")
        self.stdout.write("")

        for name, expires in keys_config:
            key, raw = CronApiKey.generate(name=name, expires_days=expires)
            exp_str = key.expires_at.strftime("%Y-%m-%d") if key.expires_at else "Nunca"
            self.stdout.write(f"  {name}")
            self.stdout.write(f"    Token: {raw}")
            self.stdout.write(f"    Expira: {exp_str}")
            self.stdout.write("")

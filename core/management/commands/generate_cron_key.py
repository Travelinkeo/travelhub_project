from django.core.management.base import BaseCommand

from core.models.cron_api_key import CronApiKey


class Command(BaseCommand):
    """Comando de gestión personalizado."""
    help = "Genera una nueva CronApiKey para usar en cron-job.org"

    def add_arguments(self, parser):
        """Método: add arguments."""
        parser.add_argument("--name", required=True, help="Nombre descriptivo de la key")
        parser.add_argument(
            "--expires", type=int, default=90, help="Dias hasta expiracion (default: 90)"
        )

    def handle(self, *args, **options):
        """Método: handle."""
        name = options["name"]
        expires = options["expires"]

        key, raw = CronApiKey.generate(name=name, expires_days=expires)

        self.stdout.write(self.style.SUCCESS(f"CronApiKey creada: {name}"))
        self.stdout.write(f"  Prefijo:  {key.prefix}...")
        self.stdout.write(
            f"  Expira:   {key.expires_at.strftime('%Y-%m-%d') if key.expires_at else 'Nunca'}"
        )
        self.stdout.write(f"  Token:    {raw}")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Guarda el token ahora. No se mostrara de nuevo."))
        self.stdout.write("Usalo en cron-job.org como valor de X-Cron-Token.")

import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.models.agencia import Agencia


class Command(BaseCommand):
    """Comando de gestión personalizado."""
    help = "Crea/actualiza la agencia piloto por defecto para el dominio principal (MAIN_DOMAIN)"

    def add_arguments(self, parser):
        """Método: add arguments."""
        parser.add_argument(
            "--domain",
            type=str,
            default=None,
            help="Dominio a mapear (default: valor de env MAIN_DOMAIN)",
        )
        parser.add_argument(
            "--superuser",
            type=str,
            default="admin",
            help="Username del superusuario propietario (default: admin)",
        )

    def handle(self, *args, **options):
        """Método: handle."""
        main_domain = options["domain"] or os.getenv("MAIN_DOMAIN", "travelhub.cc")
        username = options["superuser"]

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"is_superuser": True, "is_staff": True, "email": f"admin@{main_domain}"},
        )
        if created:
            user.set_password("TravelHub2026!")
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Superusuario "{username}" creado'))

        agencia, created = Agencia.objects.update_or_create(
            dominio_personalizado=main_domain,
            defaults={
                "nombre": f"TravelHub [{main_domain}]",
                "nombre_comercial": "TravelHub",
                "email_principal": f"sistema@{main_domain}",
                "activa": True,
                "propietario": user,
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Agencia "{agencia.nombre}" creada con dominio {main_domain}')
            )
        else:
            self.stdout.write(self.style.WARNING(f'Agencia "{agencia.nombre}" actualizada'))

        if agencia.configuracion:
            cfg = agencia.configuracion
            cfg.moneda_principal = "USD"
            cfg.plan = "FREE"
            cfg.plan_status = "active"
            cfg.save(update_fields=["moneda_principal", "plan", "plan_status"])

        if agencia.branding:
            branding = agencia.branding
            branding.color_primario = "#1976d2"
            branding.ui_theme = "obsidian"
            branding.save(update_fields=["color_primario", "ui_theme"])

        self.stdout.write(self.style.SUCCESS(f'Agencia "{agencia.nombre}" configurada y activa'))

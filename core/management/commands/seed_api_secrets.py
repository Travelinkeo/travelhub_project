import logging
import os

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

ENV_TO_SECRET = {
    "OPENAI_API_KEY": {
        "category": "ai",
        "description": "OpenAI — modelo principal con cobertura total",
    },
    "DEEPSEEK_API_KEY": {
        "category": "ai",
        "description": "DeepSeek — fallback de emergencia (solo texto plano)",
    },
    "STRIPE_SECRET_KEY": {
        "category": "payment",
        "description": "Stripe Secret Key (procesamiento de pagos)",
    },
    "STRIPE_WEBHOOK_SECRET": {"category": "payment", "description": "Stripe Webhook Secret"},
    "RESEND_API_KEY": {
        "category": "email",
        "description": "Resend — envío de correos transaccionales",
    },
    "CLOUDFLARE_R2_ACCESS_KEY_ID": {
        "category": "storage",
        "description": "Cloudflare R2 Access Key ID",
    },
    "CLOUDFLARE_R2_SECRET_ACCESS_KEY": {
        "category": "storage",
        "description": "Cloudflare R2 Secret Access Key",
    },
    "TELEGRAM_BOT_TOKEN": {
        "category": "messaging",
        "description": "Telegram Bot Token (notificaciones)",
    },
    "GOOGLE_MAPS_API_KEY": {"category": "maps", "description": "Google Maps API Key"},
    "TWILIO_ACCOUNT_SID": {"category": "messaging", "description": "Twilio Account SID (SMS)"},
    "TWILIO_AUTH_TOKEN": {"category": "messaging", "description": "Twilio Auth Token"},
    "SENTRY_DSN": {"category": "monitoring", "description": "Sentry DSN (monitoreo de errores)"},
    "HONEYCOMB_API_KEY": {"category": "monitoring", "description": "Honeycomb API Key (trazas)"},
    "MAPBOX_TOKEN": {"category": "maps", "description": "Mapbox Token"},
    "GOOGLE_OAUTH_CLIENT_ID": {"category": "security", "description": "Google OAuth Client ID"},
    "GOOGLE_OAUTH_CLIENT_SECRET": {
        "category": "security",
        "description": "Google OAuth Client Secret",
    },
    "MICROSOFT_OAUTH_CLIENT_ID": {
        "category": "security",
        "description": "Microsoft OAuth Client ID",
    },
    "MICROSOFT_OAUTH_CLIENT_SECRET": {
        "category": "security",
        "description": "Microsoft OAuth Client Secret",
    },
    "EVOLUTION_API_KEY": {"category": "whatsapp", "description": "Evolution API Key"},  # noqa: E501
}


class Command(BaseCommand):
    """Comando de gestión personalizado."""
    help = "Siembra en APISecret las claves definidas en variables de entorno"

    def handle(self, *args, **options):
        """Método: handle."""
        from core.models import APISecret

        created = 0
        updated = 0
        skipped = 0

        for env_var, meta in ENV_TO_SECRET.items():
            value = os.getenv(env_var)
            if not value:
                skipped += 1
                continue

            obj, is_new = APISecret.objects.update_or_create(
                service=env_var,
                defaults={
                    "category": meta["category"],
                    "value": value,
                    "description": meta["description"],
                    "is_active": True,
                },
            )
            if is_new:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ {env_var}"))
            else:
                updated += 1
                self.stdout.write(self.style.WARNING(f"  ~ {env_var} (actualizada)"))

        self.stdout.write()
        self.stdout.write(
            self.style.SUCCESS(
                f"Completado: {created} creadas, {updated} actualizadas, {skipped} omitidas (no definidas en entorno)."
            )
        )

import hashlib
import logging
import secrets

from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class CronApiKey(models.Model):
    """API Key para autenticar cron jobs HTTP en lugar de usar SECRET_KEY."""

    agencia = models.ForeignKey(
        "core.Agencia",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Si es null, es una key global de plataforma",
    )
    key_hash = models.CharField(max_length=128, unique=True, editable=False)
    name = models.CharField(max_length=100, help_text="Ej: cron-job.org BCV sync")
    prefix = models.CharField(max_length=12, editable=False, help_text="Primeros 8 chars para identificar")
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Cron API Key"
        verbose_name_plural = "Cron API Keys"

    def __str__(self):
        return f"{self.name} ({self.prefix}...)"

    @classmethod
    def generate(cls, name, agencia=None, expires_days=90):
        raw_key = f"cron_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:10]
        expires_at = timezone.now() + timezone.timedelta(days=expires_days) if expires_days else None

        instance = cls.objects.create(
            agencia=agencia,
            key_hash=key_hash,
            name=name,
            prefix=prefix,
            expires_at=expires_at,
        )
        logger.info(f"CronApiKey creada: {name} ({prefix}...)")
        return instance, raw_key

    @classmethod
    def verify(cls, token):
        if not token:
            return None
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            key = cls.objects.get(key_hash=key_hash, is_active=True)
            if key.expires_at and key.expires_at < timezone.now():
                logger.warning(f"CronApiKey expirada: {key.name}")
                return None
            key.last_used = timezone.now()
            key.save(update_fields=["last_used"])
            return key
        except cls.DoesNotExist:
            return None

    def revoke(self):
        self.is_active = False
        self.save(update_fields=["is_active"])
        logger.info(f"CronApiKey revocada: {self.name}")

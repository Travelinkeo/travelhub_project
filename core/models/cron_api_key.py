import hashlib
import logging
import secrets

from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)

PBKDF2_ITERATIONS = 600_000


def _hash_key(raw_key: str, salt: str | None = None) -> tuple[str, str]:
    """Genera hash PBKDF2 de la clave. Retorna (salt_hex, hash_hex)."""
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", raw_key.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return salt, dk.hex()


def _verify_key(raw_key: str, stored_hash: str) -> bool:
    """Verifica clave contra hash. Soporta PBKDF2 (salt$hash) y SHA256 legacy."""
    if "$" in stored_hash:
        salt, expected = stored_hash.split("$", 1)
        _, computed = _hash_key(raw_key, salt)
        return computed == expected
    return hashlib.sha256(raw_key.encode()).hexdigest() == stored_hash


class CronApiKey(models.Model):
    """API Key para autenticar cron jobs HTTP en lugar de usar SECRET_KEY."""

    agencia = models.ForeignKey(
        "core.Agencia",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Si es null, es una key global de plataforma",
    )
    salt = models.CharField(
        max_length=32,
        default="",
        editable=False,
        help_text="Salt aleatorio para PBKDF2 (hex). Vacío para keys legacy.",
    )
    lookup_hash = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        editable=False,
        help_text="SHA-256 del raw key para O(1) lookup en verify()",
    )
    key_hash = models.CharField(max_length=256, unique=True, editable=False)
    name = models.CharField(max_length=100, help_text="Ej: cron-job.org BCV sync")
    prefix = models.CharField(
        max_length=12, editable=False, help_text="Primeros 8 chars para identificar"
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        """Meta definición del modelo."""
        verbose_name = "Cron API Key"
        verbose_name_plural = "Cron API Keys"

    def __str__(self):
        return f"{self.name} ({self.prefix}...)"

    @classmethod
    def generate(cls, name, agencia=None, expires_days=90):
        """Método: generate."""
        raw_key = f"cron_{secrets.token_urlsafe(32)}"
        salt, key_hash_pbkdf2 = _hash_key(raw_key)
        prefix = raw_key[:10]
        lookup_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        expires_at = (
            timezone.now() + timezone.timedelta(days=expires_days) if expires_days else None
        )

        instance = cls.objects.create(
            agencia=agencia,
            salt=salt,
            lookup_hash=lookup_hash,
            key_hash=f"{salt}${key_hash_pbkdf2}",
            name=name,
            prefix=prefix,
            expires_at=expires_at,
        )
        logger.info(f"CronApiKey creada: {name} ({prefix}...)")
        return instance, raw_key

    @classmethod
    def verify(cls, token):
        """Método: verify."""
        if not token:
            return None

        computed_lookup = hashlib.sha256(token.encode()).hexdigest()
        key = cls.objects.filter(lookup_hash=computed_lookup, is_active=True).first()
        if key:
            if key.expires_at and key.expires_at < timezone.now():
                logger.warning(f"CronApiKey expirada: {key.name}")
                return None
            key.last_used = timezone.now()
            key.save(update_fields=["last_used"])
            return key

        prefix = token[:10]
        candidates = cls.objects.filter(prefix=prefix, is_active=True, lookup_hash__isnull=True)
        for key in candidates:
            if not _verify_key(token, key.key_hash):
                continue
            if key.expires_at and key.expires_at < timezone.now():
                logger.warning(f"CronApiKey expirada: {key.name}")
                continue
            key.last_used = timezone.now()
            key.save(update_fields=["last_used"])
            return key
        return None

    def revoke(self):
        """Método: revoke."""
        self.is_active = False
        self.save(update_fields=["is_active"])
        logger.info(f"CronApiKey revocada: {self.name}")

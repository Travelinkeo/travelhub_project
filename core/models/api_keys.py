"""
API Keys para la API pública de TravelHub.

DEPRECATED — La tabla 'core_apikey' fue eliminada en la migración 0049.
Este modelo Python y sus importadores (core/api/public_auth.py,
core/api/public_views.py, core/api/public_serializers.py,
tests/test_api_keys_webhooks.py) son dead code y solo persisten
para referencia. NO usar en producción.

Ver CronApiKey (core/models/cron_api_key.py) como reemplazo activo.
"""

import hashlib
import logging
import secrets
import warnings

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)

warnings.warn(
    "core.models.api_keys está DEPRECATED (tabla eliminada en migración 0049). "
    "Usar core.models.cron_api_key.CronApiKey en su lugar.",
    DeprecationWarning,
    stacklevel=2,
)

PBKDF2_ITERATIONS = 600_000


def _hash_key(raw_key: str, salt: str | None = None) -> tuple[str, str]:
    """
    Genera un hash PBKDF2 de la clave.

    Args:
        raw_key: La clave en texto plano.
        salt: Salt hexadecimal (opcional; se genera una nueva si no se provee).

    Returns:
        Tuple de (salt_hex, hash_hex).
    """
    if salt is None:
        salt = secrets.token_hex(16)
    key_bytes = raw_key.encode("utf-8")
    salt_bytes = salt.encode("utf-8")
    dk = hashlib.pbkdf2_hmac("sha256", key_bytes, salt_bytes, PBKDF2_ITERATIONS)
    return salt, dk.hex()


def _verify_key(raw_key: str, stored_hash: str) -> bool:
    """
    Verifica una clave contra un hash almacenado.

    Soporta dos formatos:
    - Nuevo: ``salt_hex$hash_hex`` (PBKDF2)
    - Legacy: ``hash_hex`` (SHA256 directo, para migración)
    """
    if "$" in stored_hash:
        salt, expected_hash = stored_hash.split("$", 1)
        _, computed_hash = _hash_key(raw_key, salt)
        return computed_hash == expected_hash
    else:
        return hashlib.sha256(raw_key.encode()).hexdigest() == stored_hash


class APIKeyPlan(models.TextChoices):
    """Planes disponibles con sus rate limits por hora."""

    TRIAL = "trial", "Trial (100 req/hora)"
    BASICO = "basico", "Básico (1,000 req/hora)"
    PROFESIONAL = "profesional", "Profesional (5,000 req/hora)"
    ENTERPRISE = "enterprise", "Enterprise (50,000 req/hora)"


# Rate limits por plan (requests por hora)
RATE_LIMITS = {
    APIKeyPlan.TRIAL: 100,
    APIKeyPlan.BASICO: 1000,
    APIKeyPlan.PROFESIONAL: 5000,
    APIKeyPlan.ENTERPRISE: 50000,
}


class APIKey(models.Model):
    """
    API Key para autenticar requests a la API pública.

    La key raw nunca se almacena — solo el hash SHA-256.
    El prefijo ( primeros 8 chars) se guarda para identificación.
    """

    def __init__(self, *args, **kwargs):
        from django.conf import settings

        if not getattr(settings, "DEBUG", True):
            raise RuntimeError("APIKey no se puede instanciar en produccion. Usa CronApiKey.")
        super().__init__(*args, **kwargs)

    agencia = models.ForeignKey(
        "core.Agencia",
        on_delete=models.CASCADE,
        related_name="api_keys",
        help_text="Agencia propietaria de esta API key",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_keys",
        help_text="Usuario que creó la API key",
    )
    salt = models.CharField(
        max_length=32,
        default="",
        editable=False,
        help_text="Salt aleatorio para PBKDF2 (hex). Vacío para keys legacy con SHA256.",
    )
    lookup_hash = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        editable=False,
        help_text="SHA-256 del raw key para O(1) lookup en verify()",
    )
    key_hash = models.CharField(
        max_length=256,
        unique=True,
        editable=False,
        help_text="Hash de la API key (formato salt$hash para PBKDF2, o SHA256 legacy)",
    )
    prefix = models.CharField(
        max_length=12,
        editable=False,
        help_text="Primeros 8 caracteres para identificación",
    )
    name = models.CharField(
        max_length=100,
        help_text="Nombre descriptivo (Ej: 'Integración Xero')",
    )
    plan = models.CharField(
        max_length=20,
        choices=APIKeyPlan.choices,
        default=APIKeyPlan.TRIAL,
        help_text="Plan que determina el rate limit",
    )
    rate_limit = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        help_text="Requests por hora (se actualiza al cambiar plan)",
    )
    scopes = models.JSONField(
        default=list,
        blank=True,
        help_text="Scopes permitidos (Ej: ['read:ventas', 'write:boletos'])",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Deshabilitar sin eliminar",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha de expiración (null = sin expirar)",
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Última vez que se usó esta key",
    )
    request_count = models.PositiveIntegerField(
        default=0,
        help_text="Contador total de requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["key_hash"], name="idx_apikey_hash"),
            models.Index(fields=["agencia", "is_active"], name="idx_apikey_agencia"),
        ]

    def __str__(self):
        return f"{self.name} ({self.prefix}...) [{self.get_plan_display()}]"

    @classmethod
    def generate(cls, agencia, user, name, plan=APIKeyPlan.TRIAL, scopes=None, expires_days=90):
        """
        Genera una nueva API key y retorna (instance, raw_key).
        raw_key solo se muestra una vez al usuario.
        """
        raw_key = f"th_{secrets.token_urlsafe(32)}"
        salt, key_hash_pbkdf2 = _hash_key(raw_key)
        prefix = raw_key[:10]
        lookup_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        rate_limit = RATE_LIMITS.get(plan, 100)
        expires_at = (
            timezone.now() + timezone.timedelta(days=expires_days) if expires_days else None
        )

        instance = cls.objects.create(
            agencia=agencia,
            user=user,
            salt=salt,
            lookup_hash=lookup_hash,
            key_hash=f"{salt}${key_hash_pbkdf2}",
            prefix=prefix,
            name=name,
            plan=plan,
            rate_limit=rate_limit,
            scopes=scopes or [],
            expires_at=expires_at,
        )
        logger.info(f"APIKey creada: {name} ({prefix}...) para agencia {agencia.id}")
        return instance, raw_key

    @classmethod
    def verify(cls, token):
        """
        Valida un token raw y retorna la APIKey o None.
        Actualiza last_used_at y request_count.
        """
        if not token:
            return None

        computed_lookup = hashlib.sha256(token.encode()).hexdigest()
        api_key = cls.objects.filter(lookup_hash=computed_lookup, is_active=True).first()
        if api_key:
            if api_key.expires_at and api_key.expires_at < timezone.now():
                logger.warning(f"APIKey expirada: {api_key.name}")
                return None
            cls.objects.filter(pk=api_key.pk).update(
                last_used_at=timezone.now(),
                request_count=models.F("request_count") + 1,
            )
            return api_key

        prefix = token[:10]
        candidates = cls.objects.filter(prefix=prefix, is_active=True, lookup_hash__isnull=True)
        for api_key in candidates:
            if not _verify_key(token, api_key.key_hash):
                continue
            if api_key.expires_at and api_key.expires_at < timezone.now():
                logger.warning(f"APIKey expirada: {api_key.name}")
                continue
            cls.objects.filter(pk=api_key.pk).update(
                last_used_at=timezone.now(),
                request_count=models.F("request_count") + 1,
            )
            return api_key
        return None

    def revoke(self):
        """Deshabilita la API key."""
        self.is_active = False
        self.save(update_fields=["is_active"])
        logger.info(f"APIKey revocada: {self.name} ({self.prefix}...)")

    def update_plan(self, new_plan):
        """Actualiza el plan y el rate limit."""
        self.plan = new_plan
        self.rate_limit = RATE_LIMITS.get(new_plan, self.rate_limit)
        self.save(update_fields=["plan", "rate_limit", "updated_at"])

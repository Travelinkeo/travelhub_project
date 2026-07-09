"""
API Keys para la API pública de TravelHub.

Cada agencia puede generar múltiples API keys con rate limits
diferentes según su plan de suscripción.
"""

import hashlib
import logging
import secrets

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


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
    key_hash = models.CharField(
        max_length=128,
        unique=True,
        editable=False,
        help_text="SHA-256 hash de la API key",
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
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:10]
        rate_limit = RATE_LIMITS.get(plan, 100)
        expires_at = (
            timezone.now() + timezone.timedelta(days=expires_days) if expires_days else None
        )

        instance = cls.objects.create(
            agencia=agencia,
            user=user,
            key_hash=key_hash,
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

        key_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            api_key = cls.objects.select_related("agencia").get(key_hash=key_hash, is_active=True)
            # Verificar expiración
            if api_key.expires_at and api_key.expires_at < timezone.now():
                logger.warning(f"APIKey expirada: {api_key.name}")
                return None
            # Actualizar uso
            cls.objects.filter(pk=api_key.pk).update(
                last_used_at=timezone.now(),
                request_count=models.F("request_count") + 1,
            )
            return api_key
        except cls.DoesNotExist:
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

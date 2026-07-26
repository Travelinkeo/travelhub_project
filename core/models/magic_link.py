import secrets
import uuid

from django.db import models
from django.utils import timezone


class MagicLinkToken(models.Model):
    """MagicLinkToken."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(db_index=True)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    redirect_url = models.URLField(max_length=500, blank=True, default="")
    is_onboarding = models.BooleanField(default=False)
    onboarding_data = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Magic Link Token"
        verbose_name_plural = "Magic Link Tokens"
        ordering = ["-created_at"]

    @property
    def is_valid(self):
        if self.used_at is not None:
            return False
        return timezone.now() < self.expires_at

    @classmethod
    def generate_token(cls):
        return secrets.token_urlsafe(48)

    def mark_used(self):
        """mark_used."""
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])

    def __str__(self):
        """__str__."""
        return f"MagicLink({self.email}, {'valid' if self.is_valid else 'expired/used'})"

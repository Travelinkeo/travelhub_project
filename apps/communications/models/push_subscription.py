"""
Modelo de suscripción a Web Push (Push API).

Almacena suscripciones de navegadores para enviar notificaciones push.
"""

from django.conf import settings
from django.db import models


class PushSubscription(models.Model):
    """Suscripción Web Push de un navegador."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
    )
    agencia = models.ForeignKey(
        "core.Agencia",
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        null=True,
        blank=True,
    )
    endpoint = models.URLField(max_length=512, unique=True)
    auth_key = models.CharField(max_length=128)
    p256dh_key = models.CharField(max_length=256)
    user_agent = models.CharField(max_length=512, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Suscripción Push"
        verbose_name_plural = "Suscripciones Push"
        db_table = "communications_push_subscription"
        indexes = [
            models.Index(fields=["user", "active"]),
        ]

    def __str__(self):
        return f"PushSubscription({self.user_id})"

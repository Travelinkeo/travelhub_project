"""
Serializers para la gestión de API Keys y Webhooks.
"""

from rest_framework import serializers

from core.models.api_keys import APIKeyPlan  # DEPRECATED: CronApiKey has no Plan yet
from core.models.cron_api_key import CronApiKey as APIKey
from core.models.webhooks import Webhook, WebhookDelivery, WebhookEvent


class APIKeyCreateSerializer(serializers.Serializer):
    """Serializer para crear una nueva API key."""

    name = serializers.CharField(max_length=100)
    plan = serializers.ChoiceField(
        choices=APIKeyPlan.choices,
        default=APIKeyPlan.TRIAL,
    )
    scopes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    expires_days = serializers.IntegerField(
        required=False,
        default=90,
        min_value=1,
        max_value=365,
    )


class APIKeySerializer(serializers.ModelSerializer):
    """Serializer para listar/consultar API keys (sin exponer la key raw)."""

    plan_display = serializers.CharField(source="get_plan_display", read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = APIKey
        fields = [
            "id",
            "name",
            "prefix",
            "plan",
            "plan_display",
            "rate_limit",
            "scopes",
            "is_active",
            "is_expired",
            "expires_at",
            "last_used_at",
            "request_count",
            "created_at",
        ]
        read_only_fields = ["id", "prefix", "request_count", "created_at"]

    def get_is_expired(self, obj):
        if obj.expires_at is None:
            return False
        from django.utils import timezone

        return obj.expires_at < timezone.now()


class APIKeyCreatedSerializer(serializers.Serializer):
    """Serializer para la respuesta al crear una API key."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    prefix = serializers.CharField()
    plan = serializers.CharField()
    rate_limit = serializers.IntegerField()
    raw_key = serializers.CharField(help_text="GUARDAR: solo se muestra una vez")
    expires_at = serializers.DateTimeField(allow_null=True)


class WebhookSerializer(serializers.ModelSerializer):
    """Serializer para CRUD de webhooks."""

    events_display = serializers.SerializerMethodField()
    delivery_stats = serializers.SerializerMethodField()

    class Meta:
        model = Webhook
        fields = [
            "id",
            "url",
            "events",
            "events_display",
            "is_active",
            "description",
            "last_triggered_at",
            "last_success_at",
            "failure_count",
            "total_deliveries",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "last_triggered_at",
            "last_success_at",
            "failure_count",
            "total_deliveries",
            "created_at",
        ]

    def get_events_display(self, obj):
        return [{"value": e, "label": dict(WebhookEvent.choices).get(e, e)} for e in obj.events]

    def get_delivery_stats(self, obj):
        return {
            "total": obj.total_deliveries,
            "failures": obj.failure_count,
            "success_rate": (
                round((obj.total_deliveries - obj.failure_count) / obj.total_deliveries * 100, 1)
                if obj.total_deliveries > 0
                else 0
            ),
        }


class WebhookDeliverySerializer(serializers.ModelSerializer):
    """Serializer para historial de entregas."""

    webhook_url = serializers.CharField(source="webhook.url", read_only=True)

    class Meta:
        model = WebhookDelivery
        fields = [
            "id",
            "webhook_url",
            "event_type",
            "response_status",
            "success",
            "error_message",
            "duration_ms",
            "created_at",
        ]


class AvailableEventsSerializer(serializers.Serializer):
    """Lista de eventos disponibles para suscribir."""

    value = serializers.CharField()
    label = serializers.CharField()

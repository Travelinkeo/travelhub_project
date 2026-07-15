"""
ViewSets para gestionar API Keys y Webhooks.

Endpoints:
    /api/v1/api-keys/           — CRUD de API keys
    /api/v1/webhooks/           — CRUD de webhooks
    /api/v1/webhooks/events/    — Lista de eventos disponibles
    /api/v1/webhooks/{id}/deliveries/ — Historial de entregas
"""

import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api.mixins.tenant import TenantViewSetMixin
from core.api.public_auth import APIKeyAuthentication
from core.api.public_serializers import (
    APIKeyCreatedSerializer,
    APIKeyCreateSerializer,
    APIKeySerializer,
    WebhookDeliverySerializer,
    WebhookSerializer,
)
from core.models.cron_api_key import CronApiKey as APIKey
from core.models.webhooks import Webhook, WebhookEvent

logger = logging.getLogger(__name__)


class APIKeyViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD de API Keys.

    - Crear: genera una key raw que solo se muestra una vez
    - Listar: muestra metadata sin exponer la key
    - Revocar: desactivar sin eliminar
    - Actualizar plan: cambiar rate limits
    """

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = APIKeySerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        return APIKey.objects.filter(
            agencia=self.request.user.usuarioagencia_set.first().agencia
            if hasattr(self.request.user, "usuarioagencia_set")
            else None,
            is_active=True,
        )

    def get_serializer_class(self):
        if self.action == "create":
            return APIKeyCreateSerializer
        return APIKeySerializer

    def create(self, request, *args, **kwargs):
        """Crear una nueva API key. La key raw solo se retorna una vez."""
        serializer = APIKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Obtener agencia del usuario
        agencia = None
        if hasattr(request.user, "usuarioagencia_set"):
            ua = request.user.usuarioagencia_set.first()
            if ua:
                agencia = ua.agencia

        if not agencia:
            return Response(
                {"error": "Usuario no tiene agencia asignada"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        api_key, raw_key = APIKey.generate(
            agencia=agencia,
            user=request.user,
            name=data["name"],
            plan=data["plan"],
            scopes=data.get("scopes", []),
            expires_days=data.get("expires_days", 90),
        )

        return Response(
            APIKeyCreatedSerializer(
                {
                    "id": api_key.id,
                    "name": api_key.name,
                    "prefix": api_key.prefix,
                    "plan": api_key.plan,
                    "rate_limit": api_key.rate_limit,
                    "raw_key": raw_key,
                    "expires_at": api_key.expires_at,
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        """Revocar (deshabilitar) una API key."""
        api_key = self.get_object()
        api_key.revoke()
        return Response({"status": "revoked", "prefix": api_key.prefix})

    @action(detail=True, methods=["post"])
    def change_plan(self, request, pk=None):
        """Cambiar el plan y rate limit de una API key."""
        api_key = self.get_object()
        new_plan = request.data.get("plan")
        if new_plan not in dict(APIKey.choices if hasattr(APIKey, "choices") else []):
            from core.models.api_keys import APIKeyPlan  # DEPRECATED: CronApiKey has no Plan yet

            if new_plan not in dict(APIKeyPlan.choices):
                return Response(
                    {"error": f"Plan inválido: {new_plan}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        api_key.update_plan(new_plan)
        return Response(
            {
                "plan": api_key.plan,
                "rate_limit": api_key.rate_limit,
            }
        )


class WebhookViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD de Webhooks.

    - Crear: registrar URL + eventos a escuchar
    - Listar: ver webhooks activos con estadísticas
    - Pausar/Reanudar: toggle is_active
    """

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WebhookSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        return Webhook.objects.filter(
            agencia=self.request.user.usuarioagencia_set.first().agencia
            if hasattr(self.request.user, "usuarioagencia_set")
            else None,
        )

    def perform_create(self, serializer):
        agencia = None
        if hasattr(self.request.user, "usuarioagencia_set"):
            ua = self.request.user.usuarioagencia_set.first()
            if ua:
                agencia = ua.agencia
        serializer.save(agencia=agencia)

    @action(detail=True, methods=["post"])
    def toggle(self, request, pk=None):
        """Pausar/reanudar un webhook."""
        webhook = self.get_object()
        webhook.is_active = not webhook.is_active
        webhook.save(update_fields=["is_active"])
        return Response(
            {
                "is_active": webhook.is_active,
                "status": "active" if webhook.is_active else "paused",
            }
        )

    @action(detail=True, methods=["get"])
    def deliveries(self, request, pk=None):
        """Historial de entregas de un webhook específico."""
        webhook = self.get_object()
        deliveries = webhook.deliveries.all()[:50]
        serializer = WebhookDeliverySerializer(deliveries, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def events(self, request):
        """Lista de eventos disponibles para suscribir."""
        events = [{"value": value, "label": label} for value, label in WebhookEvent.choices]
        return Response(events)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Estadísticas agregadas de todos los webhooks de la agencia."""
        qs = self.get_queryset()
        total = qs.count()
        active = qs.filter(is_active=True).count()
        from django.db.models import Sum

        deliveries = qs.aggregate(
            total_deliveries=Sum("total_deliveries"),
            total_failures=Sum("failure_count"),
        )
        return Response(
            {
                "total_webhooks": total,
                "active_webhooks": active,
                "total_deliveries": deliveries["total_deliveries"] or 0,
                "total_failures": deliveries["total_failures"] or 0,
            }
        )

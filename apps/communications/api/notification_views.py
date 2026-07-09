"""
API Endpoints para gestión de Preferencias de Notificación y Plantillas.
"""

from django.db.models import Q
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.communications.models import (
    NotificationLog,
    NotificationPreference,
    NotificationTemplate,
)


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer para Preferencias de Notificación"""

    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "agencia",
            "event_type",
            "channel",
            "enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """
    CRUD de preferencias de notificación por usuario.

    Endpoints:
    - GET /api/v1/notification-preferences/ - Listar mis preferencias
    - POST /api/v1/notification-preferences/ - Crear preferencia
    - PATCH /api/v1/notification-preferences/{id}/ - Actualizar
    - DELETE /api/v1/notification-preferences/{id}/ - Eliminar
    - GET /api/v1/notification-preferences/by-event/{event_type}/ - Filtrar por evento
    - POST /api/v1/notification-preferences/bulk-update/ - Actualizar múltiples
    """

    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    queryset = NotificationPreference.objects.none()  # Sejected en get_queryset()

    def get_queryset(self):
        """Cada usuario solo ve sus propias preferencias"""
        agencia = self.request.user.agencias.filter(activo=True).first()
        agencia_id = agencia.agencia_id if agencia else None

        return NotificationPreference.objects.filter(
            Q(user=self.request.user) & (Q(agencia_id=agencia_id) | Q(agencia__isnull=True))
        )

    @action(detail=False, methods=["get"], url_path="by-event/(?P<event_type>[\\w-]+)")
    def by_event(self, request, event_type=None):
        """Obtiene preferencias para un evento específico"""
        queryset = self.get_queryset().filter(event_type=event_type)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        """
        Actualiza múltiples preferencias de una vez.

        Payload:
        {
            "preferences": [
                {"event_type": "venta_creada", "channel": "email", "enabled": true},
                {"event_type": "venta_creada", "channel": "whatsapp", "enabled": false},
            ]
        }
        """
        agencia = request.user.agencias.filter(activo=True).first()
        agencia_id = agencia.agencia_id if agencia else None

        preferences_data = request.data.get("preferences", [])
        updated = []
        created = []

        for pref_data in preferences_data:
            pref, p_created = NotificationPreference.objects.update_or_create(
                user=request.user,
                agencia_id=agencia_id,
                event_type=pref_data["event_type"],
                channel=pref_data["channel"],
                defaults={"enabled": pref_data.get("enabled", True)},
            )
            if p_created:
                created.append(pref.id)
            else:
                updated.append(pref.id)

        return Response(
            {"status": "ok", "updated": updated, "created": created},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """
        Obtiene un resumen de preferencias agrupadas por evento.
        """
        from django.db.models import Count

        queryset = self.get_queryset()

        summary = (
            queryset.values("event_type")
            .annotate(
                total_channels=Count("id"),
                enabled_channels=Count("id", filter=Q(enabled=True)),
            )
            .order_by("event_type")
        )

        return Response({"count": len(summary), "preferences": list(summary)})


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer para Plantillas de Notificación"""

    class Meta:
        model = NotificationTemplate
        fields = [
            "id",
            "name",
            "event_type",
            "channel",
            "language",
            "subject_template",
            "body_template",
            "html_template",
            "whatsapp_template_id",
            "variables_disponibles",
            "is_active",
            "is_default",
            "agencia",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    CRUD de plantillas de notificación.

    Endpoints:
    - GET /api/v1/notification-templates/ - Listar plantillas
    - POST /api/v1/notification-templates/ - Crear plantilla
    - GET /api/v1/notification-templates/{id}/ - Detalle
    - PATCH /api/v1/notification-templates/{id}/ - Actualizar
    - DELETE /api/v1/notification-templates/{id}/ - Eliminar
    - GET /api/v1/notification-templates/by-event/{event_type}/ - Filtrar por evento
    - POST /api/v1/notification-templates/{id}/preview/ - Previsualizar
    """

    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAuthenticated]
    queryset = NotificationTemplate.objects.none()

    def get_queryset(self):
        """
        Usuarios normales ven plantillas activas de su agencia + globales.
        Staff ve todas.
        """
        if self.request.user.is_staff:
            return NotificationTemplate.objects.all()

        agencia = self.request.user.agencias.filter(activo=True).first()
        agencia_id = agencia.agencia_id if agencia else None

        return NotificationTemplate.objects.filter(
            Q(agencia_id=agencia_id) | Q(agencia__isnull=True),
            is_active=True,
        )

    @action(detail=False, methods=["get"], url_path="by-event/(?P<event_type>[\\w-]+)")
    def by_event(self, request, event_type=None):
        """Obtiene plantillas para un evento y canal específicos"""
        channel = request.query_params.get("channel", "email")
        language = request.query_params.get("language", "es")

        queryset = self.get_queryset().filter(
            event_type=event_type,
            channel=channel,
            language=language,
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        """
        Previsualiza una plantilla con datos de ejemplo.

        Payload:
        {
            "context": {
                "cliente_nombre": "Juan Pérez",
                "venta_id": "123",
                "total": "1500.00"
            }
        }
        """
        template = self.get_object()
        context = request.data.get("context", {})

        rendered = template.render(context)

        return Response(
            {
                "template_name": template.name,
                "channel": template.channel,
                "rendered": rendered,
            }
        )

    @action(detail=False, methods=["get"])
    def available_variables(self, request):
        """
        Lista variables disponibles para cada tipo de evento.
        Útil para documentar qué variables se pueden usar en plantillas.
        """
        variables = {
            "venta_creada": [
                "cliente_nombre",
                "venta_id",
                "localizador",
                "total",
                "moneda",
                "fecha_venta",
                "agencia_nombre",
                "asesor_nombre",
            ],
            "pago_confirmado": [
                "cliente_nombre",
                "venta_id",
                "monto_pago",
                "moneda",
                "fecha_pago",
                "metodo_pago",
            ],
            "recordatorio_pago": [
                "cliente_nombre",
                "venta_id",
                "monto_pendiente",
                "fecha_vencimiento",
                "dias_mora",
            ],
            "boleto_importado": [
                "boleto_id",
                "pnr",
                "cliente_nombre",
                "fecha_emision",
                "aerolinea",
            ],
        }

        return Response(variables)


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer para Logs de Notificaciones (solo lectura)"""

    class Meta:
        model = NotificationLog
        fields = [
            "id",
            "event_type",
            "channel",
            "recipient",
            "subject",
            "body",
            "status",
            "error_message",
            "retry_count",
            "sent_at",
            "created_at",
        ]
        read_only_fields = fields


class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Solo lectura de logs de notificaciones.

    Endpoints:
    - GET /api/v1/notification-logs/ - Listar logs
    - GET /api/v1/notification-logs/{id}/ - Detalle
    - GET /api/v1/notification-logs/stats/ - Estadísticas
    """

    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]
    queryset = NotificationLog.objects.none()

    def get_queryset(self):
        """Staff ve todos, usuarios solo los suyos"""
        if self.request.user.is_staff:
            return NotificationLog.objects.all().order_by("-created_at")

        agencia = self.request.user.agencias.filter(activo=True).first()
        agencia_id = agencia.agencia_id if agencia else None

        return NotificationLog.objects.filter(
            Q(user=self.request.user) | Q(agencia_id=agencia_id)
        ).order_by("-created_at")

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Obtiene estadísticas de notificaciones.

        Query params:
        - days: Cantidad de días atrás (default: 7)
        """
        from apps.communications.managers.notification_manager import get_notification_stats

        days = int(request.query_params.get("days", 7))
        stats = get_notification_stats(days=days)

        return Response(stats)


# Registrar en el router global
# from rest_framework.routers import DefaultRouter
# router = DefaultRouter()
# router.register(r"notification-preferences", NotificationPreferenceViewSet)
# router.register(r"notification-templates", NotificationTemplateViewSet)
# router.register(r"notification-logs", NotificationLogViewSet)

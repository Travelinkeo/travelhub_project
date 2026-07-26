import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views import View

from core.api.webhook_dispatcher import dispatch_webhook_event
from core.models.webhooks import Webhook, WebhookEvent
from core.security import get_agencia_from_request

logger = logging.getLogger(__name__)


class WebhookListView(LoginRequiredMixin, View):
    """Lista de webhooks con estadísticas y gestión."""

    template_name = "core/webhooks/list.html"

    def _get_agencia(self, request):
        """_get_agencia."""
        return get_agencia_from_request(request)

    def get(self, request):
        """get."""
        agencia = self._get_agencia(request)
        if not agencia:
            return render(request, self.template_name, {"error": "No hay agencia activa"})

        webhooks = Webhook.objects.filter(agencia=agencia).order_by("-created_at")
        eventos_disponibles = [{"value": v, "label": l} for v, l in WebhookEvent.choices]

        # Estadísticas agregadas
        stats = webhooks.aggregate(
            total=Count("id"),
            activos=Count("id", filter=Q(is_active=True)),
            total_entregas=Sum("total_deliveries"),
            total_fallos=Sum("failure_count"),
        )

        context = {
            "webhooks": webhooks,
            "eventos_disponibles": eventos_disponibles,
            "eventos_json": json.dumps(eventos_disponibles),
            "stats": stats,
            "current_agency": agencia,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        """post."""
        agencia = self._get_agencia(request)
        if not agencia:
            return JsonResponse({"error": "No hay agencia activa"}, status=400)

        accion = request.POST.get("accion")

        if accion == "crear":
            url = request.POST.get("url", "").strip()
            description = request.POST.get("description", "").strip()
            events_raw = request.POST.get("events", "[]")
            try:
                events = json.loads(events_raw)
            except json.JSONDecodeError:
                events = []

            if not url:
                return JsonResponse({"error": "URL es requerida"}, status=400)

            webhook = Webhook.objects.create(
                agencia=agencia,
                url=url,
                events=events,
                description=description or "",
            )
            logger.info(f"Webhook creado: {webhook.id} para agencia {agencia.id}")
            return JsonResponse({"ok": True, "id": webhook.id, "secret": webhook.secret})

        elif accion == "toggle":
            webhook_id = request.POST.get("id")
            webhook = get_object_or_404(Webhook, id=webhook_id, agencia=agencia)
            webhook.is_active = not webhook.is_active
            webhook.save(update_fields=["is_active"])
            return JsonResponse({"ok": True, "is_active": webhook.is_active})

        elif accion == "eliminar":
            webhook_id = request.POST.get("id")
            webhook = get_object_or_404(Webhook, id=webhook_id, agencia=agencia)
            webhook.delete()
            return JsonResponse({"ok": True})

        elif accion == "test":
            webhook_id = request.POST.get("id")
            webhook = get_object_or_404(Webhook, id=webhook_id, agencia=agencia)
            dispatch_webhook_event(
                "webhook.test",
                {"message": "Evento de prueba desde TravelHub", "timestamp": str(timezone.now())},
                agencia_id=agencia.id,
            )
            return JsonResponse({"ok": True, "message": "Evento de prueba enviado"})

        return JsonResponse({"error": "Acción no válida"}, status=400)


class WebhookDeliveryListView(LoginRequiredMixin, View):
    """Historial de entregas de un webhook."""

    template_name = "core/webhooks/deliveries.html"

    def _get_agencia(self, request):
        """_get_agencia."""
        return get_agencia_from_request(request)

    def get(self, request, webhook_id):
        """get."""
        agencia = self._get_agencia(request)
        if not agencia:
            return render(request, self.template_name, {"error": "No hay agencia activa"})

        webhook = get_object_or_404(Webhook, id=webhook_id, agencia=agencia)
        deliveries = webhook.deliveries.order_by("-created_at")[:100]

        stats = {
            "total": deliveries.count(),
            "exitosas": deliveries.filter(success=True).count(),
            "fallidas": deliveries.filter(success=False).count(),
            "avg_ms": (
                round(sum(d.duration_ms or 0 for d in deliveries) / deliveries.count(), 1)
                if deliveries.exists()
                else 0
            ),
        }

        context = {
            "webhook": webhook,
            "deliveries": deliveries,
            "stats": stats,
            "current_agency": agencia,
        }
        return render(request, self.template_name, context)

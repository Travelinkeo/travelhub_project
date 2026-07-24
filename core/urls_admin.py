# core/urls_admin.py
import json

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import path
from django.utils.decorators import method_decorator
from django.views import View

app_name = "core_admin"


@method_decorator(staff_member_required, name="dispatch")
class HealthDashboardView(View):
    """Dashboard de salud del sistema (admin)."""

    def get(self, request):
        from apps.automation.providerchain.health import get_health_history, get_health_summary

        summary = get_health_summary()
        history = get_health_history(hours=72)
        return render(
            request,
            "admin/health_dashboard.html",
            {
                "title": "Salud del Sistema",
                "summary": summary,
                "history": history,
                "summary_json": json.dumps(summary, indent=2, default=str),
            },
        )


@staff_member_required
def health_history_json(request):
    """Endpoint JSON con datos históricos para charts."""
    from apps.automation.providerchain.health import get_health_history

    hours = int(request.GET.get("hours", 72))
    history = get_health_history(hours=hours)
    return JsonResponse({"history": history, "hours": hours})


urlpatterns = [
    # Health Dashboard
    path("health/", HealthDashboardView.as_view(), name="health_dashboard"),
    path("health/history.json", health_history_json, name="health_history_json"),
]

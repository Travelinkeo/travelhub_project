from django.http import JsonResponse
from django.urls import path
from django.utils.html import format_html


class HealthDashboardMixin:
    """Agrega un dashboard de salud del sistema al admin."""

    def get_urls(self):
        """Método que obtiene urls. Args: según implementación. Returns: datos solicitados."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "health-summary/",
                self.admin_site.admin_view(self.health_summary_view),
                name="health-summary",
            ),
        ]
        return custom_urls + urls

    def health_summary_view(self, request):
        """Método: health summary view."""
        from apps.automation.providerchain.health import get_health_summary

        summary = get_health_summary()
        return JsonResponse(summary)

    def health_status_badge(self, request):
        """Método: health status badge."""
        from apps.automation.providerchain.health import get_health_summary

        summary = get_health_summary()
        total = summary["api_secrets"]["total"]
        fail = summary["api_secrets"]["fail"]
        providers_down = sum(1 for p in summary["providers"] if p["circuit_open"])

        if fail or providers_down:
            return format_html(
                '<span style="background:#FEE2E2;color:#991B1B;padding:2px 8px;'
                'border-radius:4px;font-size:11px;">⚠ {} problemas</span>',
                fail + providers_down,
            )
        if total == 0:
            return format_html(
                '<span style="background:#F3F4F6;color:#6B7280;padding:2px 8px;'
                'border-radius:4px;font-size:11px;">◯ Sin datos</span>'
            )
        return format_html(
            '<span style="background:#D1FAE5;color:#065F46;padding:2px 8px;'
            'border-radius:4px;font-size:11px;">✓ {} OK</span>',
            total,
        )

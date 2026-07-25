from django.views.generic import TemplateView

from core.mixins import AgencyRoleRequiredMixin


class AnalyticsDashboardView(AgencyRoleRequiredMixin, TemplateView):
    """Función: AnalyticsDashboardView."""
    template_name = "analytics/dashboard_container.html"
    allowed_roles = ["admin", "gerente"]

    def get_context_data(self, **kwargs):
        """Método que obtiene context data. Args: según implementación. Returns: datos solicitados."""
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "reportes"  # For sidebar highlighting
        return context

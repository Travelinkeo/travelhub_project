import logging

from django.views.generic import TemplateView

from core.api import SaaSAdminMixin

logger = logging.getLogger(__name__)


class LiquidacionDashboardView(SaaSAdminMixin, TemplateView):
    template_name = "finance/liquidaciones_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Liquidaciones"
        return context

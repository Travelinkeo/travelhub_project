import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from core.api import get_agencia_from_request

logger = logging.getLogger(__name__)


class AIAccountingDashboardView(LoginRequiredMixin, TemplateView):
    """AIAccountingDashboardView."""

    template_name = "finance/accounting_assistant.html"

    def get_context_data(self, **kwargs):
        """get_context_data."""
        context = super().get_context_data(**kwargs)
        try:
            context["user_agencia"] = get_agencia_from_request(self.request)
        except Exception:
            context["user_agencia"] = None
        context["active_tab"] = "accounting"
        return context


# ELIMINADO: AIAccountingChatView, AIAccountingResolveProposalHTMXView,
# AIAccountingProposalsPartialView, AIChatHTMXView, PropuestaTransaccionIAListCreateAPIView,
# ResolvePropuestaAPIView - todos dependían de PropuestaTransaccionIA/ConciliacionBoleto

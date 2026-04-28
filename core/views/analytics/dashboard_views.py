from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from core.mixins import AgencyRoleRequiredMixin

class AnalyticsDashboardView(AgencyRoleRequiredMixin, TemplateView):
    template_name = "analytics/dashboard_container.html"
    allowed_roles = ['admin', 'gerente']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'reportes' # For sidebar highlighting
        return context

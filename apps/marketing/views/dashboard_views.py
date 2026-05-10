from django.views.generic import TemplateView
from apps.bookings.models import HotelTarifario
from apps.marketing.models import Campania, ActivoMarketing

class MarketingDashboardView(TemplateView):
    template_name = 'marketing/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['campanias'] = Campania.objects.all().order_by('-id')[:5]
        context['hoteles'] = HotelTarifario.objects.all()
        context['activos_recientes'] = ActivoMarketing.objects.all().order_by('-fecha_creacion')[:10]
        return context
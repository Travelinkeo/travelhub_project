from django.views.generic import TemplateView
from apps.bookings.models import HotelTarifario

class SocialHubView(TemplateView):
    template_name = 'marketing/social_hub.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hoteles'] = HotelTarifario.objects.all()
        return context
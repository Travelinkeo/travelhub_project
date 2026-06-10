from django.views.generic import TemplateView

from apps.marketing.models import ActivoMarketing, Campania
from core.api import get_user_active_agency


def _get_hotel_tarifario():
    from django.apps import apps

    return apps.get_model("bookings", "HotelTarifario")


class MarketingDashboardView(TemplateView):
    template_name = "marketing/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agencia = get_user_active_agency(self.request.user)
        if agencia:
            context["campanias"] = Campania.objects.filter(agencia=agencia).order_by("-id")[:5]
            HotelTarifario = _get_hotel_tarifario()
            context["hoteles"] = HotelTarifario.objects.filter(agencia=agencia)
            context["activos_recientes"] = ActivoMarketing.objects.filter(agencia=agencia).order_by(
                "-fecha_creacion"
            )[:10]
        else:
            context["campanias"] = Campania.objects.none()
            HotelTarifario = _get_hotel_tarifario()
            context["hoteles"] = HotelTarifario.objects.none()
            context["activos_recientes"] = ActivoMarketing.objects.none()
        return context

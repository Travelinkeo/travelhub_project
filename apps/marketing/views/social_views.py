"""Vistas (views) de la aplicación marketing.
"""

from django.views.generic import TemplateView

from core.api import get_user_active_agency


def _get_hotel_tarifario():
    # _get_hotel_tarifario:  get hotel tarifario. Args: según implementación. Returns: según implementación.
    from django.apps import apps

    return apps.get_model("bookings", "HotelTarifario")


class SocialHubView:
    """Vista para gestionar socialhub. Uso: instanciar según necesidad del dominio.
    """
    template_name = "marketing/social_hub.html"

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        context = super().get_context_data(**kwargs)
        agencia = get_user_active_agency(self.request.user)
        HotelTarifario = _get_hotel_tarifario()
        if agencia:
            context["hoteles"] = HotelTarifario.objects.filter(agencia=agencia)
        else:
            context["hoteles"] = HotelTarifario.objects.none()
        return context

import logging

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views import View

logger = logging.getLogger(__name__)


class PublicItineraryView(View):
    """
    Vista pública de itinerario para pasajeros (alias legacy v/<uuid:token>/).
    Delega en la implementación principal de apps/bookings.
    """

    def get(self, request, token):
        from apps.bookings.views.itinerary_views import public_itinerary_view

        return public_itinerary_view(request, token)


class PublicVoucherPDFView(View):
    """
    Descarga pública de voucher en PDF.
    """

    def get(self, request, token):
        from django.core.signing import BadSignature, SignatureExpired

        from apps.bookings.models import Venta
        from apps.bookings.services.itinerary_service import ItineraryCryptoService
        from core.api import Agencia, agency_context

        try:
            venta_id, agencia_id = ItineraryCryptoService.verificar_y_desempaquetar_token(
                token, max_age_days=30
            )
        except (SignatureExpired, BadSignature):
            raise Http404("El enlace ha expirado o no es válido.") from None

        agencia = get_object_or_404(Agencia, pk=agencia_id)

        with agency_context(agencia):
            venta = get_object_or_404(
                Venta.all_objects, pk=venta_id, agencia_id=agencia_id, is_deleted=False
            )
            from core.views.voucher_views import generar_voucher

            return generar_voucher(request, venta_id=venta.id)


class PublicHotelVoucherPDFView(View):
    """
    Descarga pública de voucher de hotel en PDF.
    """

    def get(self, request, alojamiento_id):
        from apps.bookings.models.componentes import AlojamientoReserva
        from core.api import agency_context
        from core.views.voucher_views import generar_voucher

        alojamiento = get_object_or_404(AlojamientoReserva, pk=alojamiento_id)
        venta = alojamiento.venta

        with agency_context(venta.agencia):
            return generar_voucher(request, venta_id=venta.id)

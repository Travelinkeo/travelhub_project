from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from apps.bookings.models import Venta
from apps.bookings.services.itinerary_service import ItineraryCryptoService


class PortalHomeView(View):
    """Landing page del portal del pasajero con formulario de búsqueda."""

    template_name = "core/portal/home.html"

    def get(self, request):
        """get."""
        return render(request, self.template_name)


class PortalLookupView(View):
    """
    Busca una reserva por localizador + apellido del pasajero.
    Si coincide, genera un token y redirige al itinerario.
    """

    def post(self, request):
        """post."""
        localizador = request.POST.get("localizador", "").strip().upper()
        apellido = request.POST.get("apellido", "").strip().upper()

        if not localizador or not apellido:
            return render(
                request,
                "core/portal/home.html",
                {"error": "Debe ingresar el localizador y su apellido."},
            )

        venta = (
            Venta.all_objects.filter(localizador__iexact=localizador, is_deleted=False)
            .select_related("agencia")
            .prefetch_related("pasajeros")
            .first()
        )

        if not venta:
            return render(
                request,
                "core/portal/home.html",
                {"error": "No encontramos una reserva con ese localizador."},
            )

        pasajero = venta.pasajeros.filter(apellidos__icontains=apellido).first()
        if not pasajero:
            return render(
                request,
                "core/portal/home.html",
                {
                    "error": "No encontramos un pasajero con ese apellido en la reserva.",
                    "localizador": localizador,
                },
            )

        token = ItineraryCryptoService.generar_enlace_itinerario(venta)
        path = reverse("bookings:public_itinerary_interactive", kwargs={"token": token})
        return HttpResponseRedirect(path)


class PortalTokenRedirectView(View):
    """
    Toma un token (UUID) legacy y lo convierte al token firmado para el nuevo portal.
    """

    def get(self, request, uuid_token):
        """get."""
        venta = Venta.all_objects.filter(uuid=uuid_token, is_deleted=False).first()
        if not venta:
            raise Http404("Reserva no encontrada.")

        token = ItineraryCryptoService.generar_enlace_itinerario(venta)
        path = reverse("bookings:public_itinerary_interactive", kwargs={"token": token})
        return HttpResponseRedirect(path)

from django.core.signing import BadSignature, SignatureExpired
from django.http import Http404
from django.shortcuts import render

from ..models import Venta
from ..services.itinerary_service import ItineraryCryptoService


def public_itinerary_view(request, token):
    """
    Vista de acceso público seguro para pasajeros.
    Renderiza el itinerario vivo utilizando tokens criptográficos temporales.
    """
    try:
        # 1. Validar firma del token y vigencia (por ejemplo, max 30 días desde emisión)
        venta_id, agencia_id = ItineraryCryptoService.verificar_y_desempaquetar_token(
            token, max_age_days=30
        )

    except (SignatureExpired, BadSignature):
        # Si el token expiró o fue alterado, mostramos una plantilla elegante de enlace vencido
        return render(request, "bookings/itinerary_expired.html", status=403)

    from core.middleware.tenant import agency_context
    from core.models.agencia import Agencia

    try:
        agencia = Agencia.objects.get(pk=agencia_id)
    except Agencia.DoesNotExist:
        raise Http404("La agencia vinculada al itinerario no existe.") from None

    with agency_context(agencia):
        # 2. Consulta optimizada en una sola transacción SQL (Multi-Tenant Guard explícito)
        try:
            venta = (
                Venta.all_objects.select_related("agencia")
                .prefetch_related(
                    "pasajeros",
                    "pagos_venta",  # Relación del motor de recaudación
                    "pagos_venta__moneda",  # Prefetch moneda para listado de pagos
                    "segmentos_vuelo",  # Prefetch segmentos de vuelo
                    "segmentos_vuelo__origen",  # Prefetch origen
                    "segmentos_vuelo__destino",  # Prefetch destino
                    "alojamientos",  # Prefetch alojamientos
                    "alquileres_autos",  # Prefetch alquileres
                    "traslados",  # Prefetch traslados
                    "servicios_adicionales",  # Prefetch servicios adicionales
                )
                .get(pk=venta_id, agencia_id=agencia_id, is_deleted=False)
            )
        except Venta.DoesNotExist:
            raise Http404("El itinerario solicitado no se encuentra en los registros.") from None

        # 3. Detectar si una sub-sección es llamada asíncronamente por HTMX (ej: recargar el clima o estatus de vuelo)
        is_htmx = request.headers.get("HX-Request") == "true" or request.headers.get("HX-Request")
        if is_htmx:
            return render(
                request, "bookings/partials/itinerary_live_timeline.html", {"venta": venta}
            )

        # Renderizado inicial de la página completa
        return render(
            request,
            "bookings/itinerary_live_page.html",
            {"venta": venta, "token": token, "agencia": venta.agencia},
        )

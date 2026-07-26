import logging

from django.core.signing import BadSignature, SignatureExpired
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views import View

from core.models.aeropuerto import Aeropuerto

from ..models import Venta
from ..services.itinerary_service import ItineraryCryptoService

logger = logging.getLogger(__name__)


def _enrich_segments(venta):
    """Añade coordenadas geográficas a segmentos de vuelo para el mapa."""
    for seg in venta.segmentos_vuelo.all():
        try:
            if seg.origen and seg.origen.codigo_iata:
                apt = Aeropuerto.objects.filter(codigo_iata=seg.origen.codigo_iata).first()
                seg._origen_lat = apt.latitud if apt else None
                seg._origen_lng = apt.longitud if apt else None
            if seg.destino and seg.destino.codigo_iata:
                apt = Aeropuerto.objects.filter(codigo_iata=seg.destino.codigo_iata).first()
                seg._destino_lat = apt.latitud if apt else None
                seg._destino_lng = apt.longitud if apt else None
        except Exception:
            seg._origen_lat = seg._origen_lng = seg._destino_lat = seg._destino_lng = None


def public_itinerary_interactive_view(request, token):
    """Vista de itinerario interactivo con mapa, countdowns y actualización automática."""
    try:
        venta_id, agencia_id = ItineraryCryptoService.verificar_y_desempaquetar_token(
            token, max_age_days=30
        )
    except (SignatureExpired, BadSignature):
        return render(request, "bookings/itinerary_expired.html", status=403)

    from core.api import Agencia, agency_context

    try:
        agencia = Agencia.objects.get(pk=agencia_id)
    except Agencia.DoesNotExist:
        raise Http404("La agencia vinculada al itinerario no existe.") from None

    with agency_context(agencia):
        try:
            venta = (
                Venta.all_objects.select_related("agencia", "cliente")
                .prefetch_related(
                    "pasajeros",
                    "segmentos_vuelo",
                    "segmentos_vuelo__origen",
                    "segmentos_vuelo__destino",
                    "alojamientos",
                    "alquileres_autos",
                    "traslados",
                    "servicios_adicionales",
                )
                .get(pk=venta_id, agencia_id=agencia_id, is_deleted=False)
            )
        except Venta.DoesNotExist:
            raise Http404("El itinerario solicitado no se encuentra.") from None

        _enrich_segments(venta)

        from django.utils import timezone

        gantt_items = _get_service_dates(venta)
        gantt_start, gantt_end = _gantt_summary(gantt_items)
        ctx = {
            "venta": venta,
            "token": token,
            "agencia": agencia,
            "gantt_items": gantt_items,
            "gantt_start": gantt_start,
            "gantt_end": gantt_end,
            "now": timezone.now(),
        }

        is_htmx = request.headers.get("HX-Request") == "true"
        if is_htmx:
            return render(
                request,
                "bookings/partials/itinerary_interactive_content.html",
                ctx,
            )

        return render(
            request,
            "bookings/itinerary_interactive.html",
            ctx,
        )


class ItineraryMapDataView(View):
    """Endpoint JSON con datos geo para el mapa Leaflet."""

    def get(self, request, token):
        """get."""
        try:
            venta_id, agencia_id = ItineraryCryptoService.verificar_y_desempaquetar_token(
                token, max_age_days=30
            )
        except (SignatureExpired, BadSignature):
            return JsonResponse({"error": "Token inválido"}, status=403)

        from core.api import Agencia, agency_context

        with agency_context(Agencia.objects.get(pk=agencia_id)):
            venta = Venta.all_objects.get(pk=venta_id, agencia_id=agencia_id, is_deleted=False)
            _enrich_segments(venta)

            routes = []
            for seg in venta.segmentos_vuelo.all():
                if seg._origen_lat and seg._origen_lng and seg._destino_lat and seg._destino_lng:
                    routes.append(
                        {
                            "from": {
                                "iata": seg.origen.codigo_iata,
                                "name": seg.origen.nombre,
                                "lat": seg._origen_lat,
                                "lng": seg._origen_lng,
                            },
                            "to": {
                                "iata": seg.destino.codigo_iata,
                                "name": seg.destino.nombre,
                                "lat": seg._destino_lat,
                                "lng": seg._destino_lng,
                            },
                            "airline": seg.aerolinea,
                            "flight": seg.numero_vuelo,
                            "date": seg.fecha_salida.isoformat() if seg.fecha_salida else None,
                        }
                    )

            return JsonResponse({"routes": routes})


def _get_service_dates(venta):
    """Retorna lista de {inicio, fin, tipo, titulo} para el Gantt."""
    items = []
    for seg in venta.segmentos_vuelo.all():
        items.append(
            {
                "title": f"{seg.aerolinea} {seg.numero_vuelo}",
                "start": seg.fecha_salida,
                "end": seg.fecha_llegada or seg.fecha_salida,
                "type": "flight",
            }
        )
    for h in venta.alojamientos.all():
        items.append(
            {
                "title": h.nombre_establecimiento,
                "start": h.check_in,
                "end": h.check_out or h.check_in,
                "type": "hotel",
            }
        )
    for a in venta.alquileres_autos.all():
        items.append(
            {
                "title": f"Auto: {a.categoria_auto}",
                "start": a.fecha_hora_retiro,
                "end": a.fecha_hora_devolucion or a.fecha_hora_retiro,
                "type": "car",
            }
        )
    return items


def _gantt_summary(gantt_items):
    """Retorna (start_date, end_date) para el Gantt."""
    starts = [i["start"] for i in gantt_items if i.get("start")]
    ends = [i["end"] for i in gantt_items if i.get("end")]
    if not starts:
        return None, None
    return min(starts), max(ends)

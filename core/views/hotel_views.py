from datetime import timedelta
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Sum
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.automation.services.ai_copywriter import AICopywriter
from apps.bookings.models import AlojamientoReserva, Amenity, HotelTarifario
from apps.bookings.services.hotel_booking_service import HotelBookingService
from apps.communications.services.marketing_service import MarketingService
from core.auth_helpers import InternalAPIAuthMixin
from core.middleware import get_current_agency


class HotelListView(LoginRequiredMixin, ListView):
    """Función: HotelListView."""
    model = HotelTarifario
    template_name = "core/hotels/search.html"
    context_object_name = "hoteles"
    paginate_by = 12

    def get_queryset(self) -> QuerySet[HotelTarifario]:
        qs = HotelTarifario.objects.filter(activo=True).prefetch_related("amenidades")
        """Método que obtiene queryset. Args: según implementación. Returns: datos solicitados."""

        # Filtro de Búsqueda General
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(nombre__icontains=q) | Q(destino__icontains=q) | Q(descripcion_larga__icontains=q)
            )

        # Filtros Específicos
        destino = self.request.GET.get("destino")
        if destino:
            qs = qs.filter(destino__iexact=destino)

        categoria = self.request.GET.get("categoria")
        if categoria:
            qs = qs.filter(categoria=categoria)

        return qs

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        """Método que obtiene context data. Args: según implementación. Returns: datos solicitados."""
        agencia = get_current_agency()

        # --- ANALÍTICA DE HOTELES (30 DÍAS) ---
        if agencia:
            hace_30_dias = timezone.now() - timedelta(days=30)
            reservas_30d = AlojamientoReserva.objects.filter(
                agencia=agencia, venta__fecha_venta__gte=hace_30_dias
            )

            # KPIs Básicos
            stats = reservas_30d.aggregate(
                total_res=Count("id_alojamiento_reserva"),
                total_revenue=Sum("item_venta__total_item_venta"),
                total_cost=Sum("item_venta__costo_neto_proveedor"),
            )

            ctx["stats_30d"] = {
                "total_reservas": stats["total_res"] or 0,
                "revenue": stats["total_revenue"] or 0,
                "margen_bruto": (stats["total_revenue"] or 0) - (stats["total_cost"] or 0),
            }

            # Top Destino
            top_dest = (
                reservas_30d.values("ciudad__nombre")
                .annotate(count=Count("id_alojamiento_reserva"))
                .order_by("-count")
                .first()
            )
            ctx["top_destino"] = top_dest["ciudad__nombre"] if top_dest else "N/A"

            # Próximos Check-ins (Hoy y Mañana)
            ctx["checkins_hoy"] = reservas_30d.filter(check_in=timezone.now().date()).count()

        # Datos para filtros laterales
        ctx["destinos"] = (
            HotelTarifario.objects.filter(activo=True)
            .values_list("destino", flat=True)
            .distinct()
            .order_by("destino")
        )
        ctx["categorias"] = HotelTarifario.CATEGORIA_CHOICES
        ctx["amenidades"] = Amenity.objects.all().order_by("nombre")
        return ctx


class HotelDetailView(LoginRequiredMixin, DetailView):
    """Función: HotelDetailView."""
    model = HotelTarifario
    template_name = "core/hotels/detail.html"
    context_object_name = "hotel"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        """Método que obtiene queryset. Args: según implementación. Returns: datos solicitados."""
        return (
            super()
            .get_queryset()
            .prefetch_related(
                "imagenes", "tipos_habitacion", "amenidades", "tipos_habitacion__tarifas"
            )
        )

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Método: post."""
        hotel = self.get_object()
        tipo_hab_id = request.POST.get("tipo_habitacion")
        check_in = request.POST.get("check_in")
        check_out = request.POST.get("check_out")

        agencia = get_current_agency()
        if not agencia:
            messages.error(request, _("No se pudo identificar la agencia activa."))
            return self.get(request, *args, **kwargs)

        try:
            venta = HotelBookingService.create_booking(
                hotel_id=hotel.pk,
                tipo_hab_id=tipo_hab_id,
                check_in=check_in,
                check_out=check_out,
                agencia=agencia,
                creado_por=request.user,
            )
            messages.success(request, f"Reserva {venta.localizador} creada exitosamente.")
            # Redirigir al admin de la venta o a una vista de éxito
            return redirect("admin:bookings_venta_change", venta.pk)
        except Exception as e:
            messages.error(request, f"Error al crear la reserva: {str(e)}")
            return self.get(request, *args, **kwargs)


def download_story_view(request: HttpRequest, slug: str) -> HttpResponse:
    """Genera y descarga la Story de Instagram"""
    hotel = HotelTarifario.objects.get(slug=slug)

    # Intentar obtener agencia del usuario logueado (si es Vendedor)
    agencia_id = None
    if request.user.is_authenticated:
        # Check if user belongs to an agency (via UsuarioAgencia or simple field)
        # Assuming simple linkage or just pass None to use default fallback in service
        pass

    img_io = MarketingService.generate_instagram_story(hotel.pk, agencia_id)

    response = HttpResponse(img_io.read(), content_type="image/jpeg")
    response["Content-Disposition"] = f'attachment; filename="story_{hotel.slug}.jpg"'
    return response


class GenerateCopyAPI(InternalAPIAuthMixin, APIView):  # type: ignore[misc]
    """Genera textos de venta para redes sociales con IA."""

    def post(self, request: HttpRequest) -> Response:
        """Método: post."""
        hotel_id = request.data.get("hotel_id")
        tone = request.data.get("tone", "AVENTURERO")

        if not hotel_id:
            return Response({"error": "Falta hotel_id"}, status=status.HTTP_400_BAD_REQUEST)

        service = AICopywriter()
        caption = service.generate_caption(hotel_id, tone)

        return Response({"caption": caption})

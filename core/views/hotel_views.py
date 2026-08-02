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
from apps.bookings.forms import TarifaHabitacionForm
from apps.bookings.models import AlojamientoReserva, Amenity, HotelTarifario
from apps.bookings.services.hotel_booking_service import HotelBookingService
from apps.communications.services.marketing_service import MarketingService
from core.auth_helpers import InternalAPIAuthMixin
from core.middleware import get_current_agency
from core.security import get_object_tenant_or_404


class HotelListView(LoginRequiredMixin, ListView):
    """HotelListView."""

    model = HotelTarifario
    template_name = "core/hotels/search.html"
    context_object_name = "hoteles"
    paginate_by = 12

    def get_queryset(self) -> QuerySet[HotelTarifario]:
        """get_queryset."""
        qs = HotelTarifario.all_objects.filter(activo=True).prefetch_related("amenidades")

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
        """get_context_data."""
        ctx = super().get_context_data(**kwargs)
        agencia = get_current_agency() or getattr(self.request, "agencia", None)

        ctx["stats_30d"] = {
            "total_reservas": 0,
            "revenue": 0,
            "margen_bruto": 0,
        }
        ctx["top_destino"] = "N/A"
        ctx["checkins_hoy"] = 0

        # --- ANALÍTICA DE HOTELES (30 DÍAS) ---
        if agencia:
            try:
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

                rev = stats["total_revenue"] or 0
                cost = stats["total_cost"] or 0
                ctx["stats_30d"] = {
                    "total_reservas": stats["total_res"] or 0,
                    "revenue": rev,
                    "margen_bruto": rev - cost,
                }

                # Top Destino
                top_dest = (
                    reservas_30d.values("ciudad__nombre")
                    .annotate(count=Count("id_alojamiento_reserva"))
                    .order_by("-count")
                    .first()
                )
                if top_dest and top_dest.get("ciudad__nombre"):
                    ctx["top_destino"] = top_dest["ciudad__nombre"]

                # Próximos Check-ins (Hoy)
                ctx["checkins_hoy"] = reservas_30d.filter(check_in=timezone.now().date()).count()
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning("Error calculando analítica de hoteles: %s", e)

        # Datos para filtros laterales
        try:
            ctx["destinos"] = (
                HotelTarifario.all_objects.filter(activo=True)
                .values_list("destino", flat=True)
                .distinct()
                .order_by("destino")
            )
            ctx["categorias"] = HotelTarifario.CATEGORIA_CHOICES
            ctx["amenidades"] = Amenity.objects.all().order_by("nombre")
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning("Error cargando filtros de hoteles: %s", e)
            ctx["destinos"] = []
            ctx["categorias"] = []
            ctx["amenidades"] = []

        return ctx


class HotelDetailView(LoginRequiredMixin, DetailView):
    """HotelDetailView."""

    model = HotelTarifario
    template_name = "core/hotels/detail.html"
    context_object_name = "hotel"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        """get_queryset."""
        return HotelTarifario.all_objects.filter(activo=True).prefetch_related(
            "imagenes", "tipos_habitacion", "amenidades", "tipos_habitacion__tarifas"
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """get_context_data."""
        ctx = super().get_context_data(**kwargs)
        hotel = self.object
        agencia = get_current_agency() or getattr(self.request, "agencia", None)

        if "tarifa_form" not in ctx:
            ctx["tarifa_form"] = TarifaHabitacionForm(hotel=hotel)

        # Filtrar tarifas por agencia activa del usuario
        for hab in hotel.tipos_habitacion.all():
            if agencia:
                hab.tarifas_agencia = list(
                    hab.tarifas.filter(Q(agencia=agencia) | Q(agencia__isnull=True))
                )
            else:
                hab.tarifas_agencia = list(hab.tarifas.all())

        return ctx

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """post."""
        hotel = self.get_object()
        action = request.POST.get("action")
        agencia = get_current_agency() or getattr(request, "agencia", None)

        if action == "agregar_tarifa":
            form = TarifaHabitacionForm(request.POST, hotel=hotel)
            if form.is_valid():
                tarifa = form.save(commit=False)
                if agencia:
                    tarifa.agencia = agencia
                tarifa.save()
                messages.success(
                    request,
                    f"Tarifa '{tarifa.nombre_temporada or 'Personalizada'}' agregada exitosamente para la agencia.",
                )
                return redirect("bookings:hotel_detail", slug=hotel.slug)
            else:
                messages.error(request, "Por favor corrige los errores en el formulario de tarifa.")
                ctx = self.get_context_data(object=hotel, tarifa_form=form)
                return self.render_to_response(ctx)

        # Lógica preexistente de reserva
        tipo_hab_id = request.POST.get("tipo_habitacion")
        check_in = request.POST.get("check_in")
        check_out = request.POST.get("check_out")

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
            return redirect("admin:bookings_venta_change", venta.pk)
        except Exception as e:
            messages.error(request, f"Error al crear la reserva: {str(e)}")
            return self.get(request, *args, **kwargs)


def download_story_view(request: HttpRequest, slug: str) -> HttpResponse:
    """Genera y descarga la Story de Instagram"""
    agencia = getattr(request, "agencia", None)
    hotel = get_object_tenant_or_404(HotelTarifario, agencia, slug=slug)

    # Intentar obtener agencia del usuario logueado (si es Vendedor)
    agencia_id = agencia.id if agencia else None

    img_io = MarketingService.generate_instagram_story(hotel.pk, agencia_id)

    response = HttpResponse(img_io.read(), content_type="image/jpeg")
    response["Content-Disposition"] = f'attachment; filename="story_{hotel.slug}.jpg"'
    return response


class GenerateCopyAPI(InternalAPIAuthMixin, APIView):  # type: ignore[misc]
    """Genera textos de venta para redes sociales con IA."""

    def post(self, request: HttpRequest) -> Response:
        """post."""
        hotel_id = request.data.get("hotel_id")
        tone = request.data.get("tone", "AVENTURERO")

        if not hotel_id:
            return Response({"error": "Falta hotel_id"}, status=status.HTTP_400_BAD_REQUEST)

        service = AICopywriter()
        caption = service.generate_caption(hotel_id, tone)

        return Response({"caption": caption})

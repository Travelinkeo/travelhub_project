import logging

from django.urls import include, path
from django.utils.module_loading import import_string
from django.views.generic import RedirectView
from rest_framework import filters, permissions, viewsets
from rest_framework.routers import DefaultRouter

from apps.bookings.bookings_views import (
    FeeVentaCreateView,
    ItemVentaCreateView,
    ItemVentaUpdateView,
    PagoVentaCreateView,
    RevenueLeakDashboardView,
    VentaCreateView,
    VentaDeleteView,
    VentaDetailView,
    VentaListView,
    VentaTimelineView,
    VentaUpdateView,
    dashboard_main,
    dashboard_stats_htmx,
    resolve_finding_htmx,
    whatsapp_pairing_code_view,
    whatsapp_qr_view,
)
from apps.bookings.models import ProductoServicio
from core.api.mixins.tenant import TenantViewSetMixin
from core.auth_helpers import InternalAPIAuthMixin

from .views import api_ingest_pnr_view, proveedores_views, public_itinerary_view
from .views.dashboard_views import DashboardView

logger = logging.getLogger(__name__)

app_name = "bookings"

router = DefaultRouter()


def dynamic_view(view_path):
    def lazy_view_handler(request, *args, **kwargs):
        view_class = import_string(view_path)
        return view_class.as_view()(request, *args, **kwargs)

    return lazy_view_handler


def dynamic_fb_view(view_path):
    def lazy_view_handler(request, *args, **kwargs):
        view_fn = import_string(view_path)
        return view_fn(request, *args, **kwargs)

    return lazy_view_handler


class ProductoServicioSerializer(viewsets.ModelViewSet):
    # This is a bit of a hack since the original had classes defined in core/urls.py
    # I should probably import them, but for now I'll just register if I can.
    pass


# We will re-use the registration logic from core/urls.py
try:
    ProductoServicioSerializer = import_string("core.serializers.ProductoServicioSerializer")
    CotizacionViewSet = import_string("apps.cotizaciones.views.CotizacionViewSet")
    ItemCotizacionViewSet = import_string("apps.cotizaciones.views.ItemCotizacionViewSet")

    class ProductoServicioViewSet(InternalAPIAuthMixin, TenantViewSetMixin, viewsets.ModelViewSet):
        queryset = ProductoServicio.objects.filter(activo=True)
        serializer_class = ProductoServicioSerializer
        permission_classes = [permissions.IsAuthenticated]
        filter_backends = [filters.SearchFilter]
        search_fields = ["nombre", "codigo_interno", "descripcion"]

    from apps.bookings.views.proveedores_views import ProveedorViewSet

    router.register(r"proveedores", ProveedorViewSet, basename="proveedor")
    router.register(r"productoservicio", ProductoServicioViewSet, basename="productoservicio")
    router.register(r"cotizaciones", CotizacionViewSet, basename="cotizaciones")
    router.register(r"items-cotizacion", ItemCotizacionViewSet, basename="items-cotizacion")
except Exception as e:
    logger.error(f"Error registering bookings ViewSets: {e}")

# Automatic Registration (Scoped to Bookings if possible, but core logic is global)
try:
    register_auto_apis = import_string("core.api_registry.register_auto_apis")
    get_registered_apis = import_string("core.api_registry.get_registered_apis")
    register_auto_apis()
    registered_apis = get_registered_apis()
    BOOKINGS_MODELS = [
        "AlquilerAutoReserva",
        "EventoServicio",
        "CircuitoTuristico",
        "CircuitoDia",
        "PaqueteAereo",
        "ServicioAdicionalDetalle",
        "Venta",
        "BoletoImportado",
        "SegmentoVuelo",
        "FeeVenta",
        "PagoVenta",
    ]
    for model_class, api_data in registered_apis.items():
        if model_class.__name__ in BOOKINGS_MODELS:
            if api_data["basename"] not in [r[2] for r in router.registry]:
                router.register(
                    api_data["path"], api_data["viewset"], basename=api_data["basename"]
                )
except Exception as e:
    logger.error(f"Error in Bookings Auto API: {e}")


urlpatterns = [
    # Rutas Core heredadas
    path("", include("apps.bookings.urls_core")),
    path("", include("apps.common.urls_core")),
    # Ventas
    path("ventas/", VentaListView.as_view(), name="venta_list"),
    path("ventas/nueva/", VentaCreateView.as_view(), name="venta_create"),
    path("ventas/<int:pk>/", VentaDetailView.as_view(), name="venta_detail"),
    path("ventas/<int:pk>/timeline/", VentaTimelineView.as_view(), name="venta_timeline"),
    path("ventas/<int:pk>/editar/", VentaUpdateView.as_view(), name="venta_update"),
    path("ventas/<int:pk>/eliminar/", VentaDeleteView.as_view(), name="venta_delete"),
    # Proveedores
    path("proveedores/", proveedores_views.ProveedorListView.as_view(), name="proveedor_list"),
    path(
        "proveedores/nuevo/",
        proveedores_views.ProveedorCreateView.as_view(),
        name="proveedor_create",
    ),
    path(
        "proveedores/<int:pk>/editar/",
        proveedores_views.ProveedorUpdateView.as_view(),
        name="proveedor_update",
    ),
    path(
        "proveedores/<int:pk>/eliminar/",
        proveedores_views.ProveedorDeleteView.as_view(),
        name="proveedor_delete",
    ),
    # Inteligencia & Auditoría
    path("auditoria/", RevenueLeakDashboardView.as_view(), name="revenue_leak_dashboard"),
    path("auditoria/<int:pk>/resolver/", resolve_finding_htmx, name="resolve_finding"),
    # HTMX Inline actions for Venta Detail
    path(
        "ventas/<int:venta_pk>/items/agregar/", ItemVentaCreateView.as_view(), name="item_venta_add"
    ),
    path("ventas/items/<int:pk>/editar/", ItemVentaUpdateView.as_view(), name="item_venta_edit"),
    path("ventas/<int:venta_pk>/fees/agregar/", FeeVentaCreateView.as_view(), name="fee_venta_add"),
    path(
        "ventas/<int:venta_pk>/pagos/agregar/", PagoVentaCreateView.as_view(), name="pago_venta_add"
    ),
    # Dashboard de Flujo de Caja
    path("dashboard/", dashboard_main, name="dashboard_main"),
    path("dashboard/stats/", dashboard_stats_htmx, name="dashboard_stats"),
    path("dashboard/modern/", DashboardView.as_view(), name="modern_dashboard"),
    path("dashboard/whatsapp-qr/", whatsapp_qr_view, name="whatsapp_qr"),
    path("dashboard/whatsapp-pairing/", whatsapp_pairing_code_view, name="whatsapp_pairing"),
    # Redirecciones Legacy
    path(
        "dashboard/erp/ventas/",
        RedirectView.as_view(pattern_name="bookings:venta_list", permanent=True),
        name="ventas_dashboard",
    ),
    # Cotizaciones
    path(
        "cotizaciones/",
        dynamic_view("apps.cotizaciones.views.CotizacionDashboardView"),
        name="cotizacion_dashboard",
    ),
    path(
        "cotizaciones/magic/",
        dynamic_view("apps.cotizaciones.views.MagicQuoterView"),
        name="cotizacion_magic",
    ),
    path(
        "cotizaciones/htmx/calcular/",
        dynamic_view("apps.cotizaciones.views.CotizacionHTMXCalculateTotalsView"),
        name="cotizacion_htmx_calcular",
    ),
    path(
        "cotizaciones/htmx/add-item/",
        dynamic_view("apps.cotizaciones.views.CotizacionHTMXAddItemView"),
        name="cotizacion_htmx_add_item",
    ),
    path(
        "cotizaciones/nueva/",
        dynamic_view("apps.cotizaciones.views.CotizacionCreateView"),
        name="cotizacion_nueva",
    ),
    path(
        "cotizaciones/<int:pk>/",
        dynamic_view("apps.cotizaciones.views.CotizacionDetailView"),
        name="cotizacion_detalle",
    ),
    path(
        "cotizaciones/<int:pk>/editar/",
        dynamic_view("apps.cotizaciones.views.CotizacionUpdateView"),
        name="cotizacion_editar",
    ),
    path(
        "cotizaciones/<int:pk>/cambiar-estado/",
        dynamic_view("apps.cotizaciones.views.CotizacionStatusView"),
        name="cotizacion_cambiar_estado",
    ),
    path(
        "cotizaciones/<int:pk>/pdf/",
        dynamic_view("apps.cotizaciones.views.CotizacionPDFView"),
        name="cotizacion_pdf",
    ),
    path(
        "cotizaciones/<int:pk>/convertir/",
        dynamic_view("apps.cotizaciones.views.CotizacionConvertirView"),
        name="cotizacion_convertir",
    ),
    path(
        "api/cotizaciones/magic-gpt/",
        dynamic_view("apps.cotizaciones.views.MagicQuoterAIView"),
        name="cotizacion_magic_gpt",
    ),
    # Hotel Engine & Marketing (Movido de core/urls.py)
    path("hoteles/", dynamic_view("core.views.hotel_views.HotelListView"), name="hotel_search"),
    path(
        "hoteles/<slug:slug>/",
        dynamic_view("core.views.hotel_views.HotelDetailView"),
        name="hotel_detail",
    ),
    path(
        "hoteles/<slug:slug>/story/",
        dynamic_fb_view("core.views.hotel_views.download_story_view"),
        name="hotel_story",
    ),
    path(
        "api/marketing/generate-copy/",
        dynamic_view("core.views.hotel_views.GenerateCopyAPI"),
        name="generate_copy_api",
    ),
    path(
        "api/marketing/generate-image/",
        dynamic_view("apps.marketing.views.marketing_views.GenerateAIImageView"),
        name="generate_ai_image",
    ),
    path(
        "marketing/hub/",
        dynamic_view("apps.marketing.views.marketing_views.MarketingHubView"),
        name="marketing_hub",
    ),
    path(
        "api/hotels/quote/",
        dynamic_view("core.api.hotel_api.HotelQuoteAPI"),
        name="hotel_quote_api",
    ),
    # Flight Search (Movido de core/urls.py)
    path(
        "flights/", dynamic_view("core.views.flights_views.FlightSearchView"), name="flight_search"
    ),
    # Vouchers
    path(
        "api/ventas/<int:venta_id>/generar-voucher/",
        dynamic_fb_view("core.views.voucher_views.generar_voucher"),
        name="generar_voucher",
    ),
    # --- VISTAS PÚBLICAS (White-Label) ---
    path(
        "v/<uuid:token>/",
        dynamic_view("core.views.public_views.PublicItineraryView"),
        name="public_itinerary",
    ),
    path(
        "v/<uuid:token>/pdf/",
        dynamic_view("core.views.public_views.PublicVoucherPDFView"),
        name="public_voucher_pdf",
    ),
    path(
        "v/hotel/<int:alojamiento_id>/pdf/",
        dynamic_view("core.views.public_views.PublicHotelVoucherPDFView"),
        name="public_hotel_voucher",
    ),
    path("itinerary/v1/live/<str:token>/", public_itinerary_view, name="public_itinerary_live"),
    path(
        "itinerary/v1/live/<str:token>/passenger/<int:pasajero_id>/ocr/",
        dynamic_fb_view("apps.bookings.views.passenger_portal.public_itinerary_ocr_upload"),
        name="public_itinerary_ocr_upload",
    ),
    path(
        "itinerary/v1/live/<str:token>/passenger/<int:pasajero_id>/save/",
        dynamic_fb_view("apps.bookings.views.passenger_portal.public_itinerary_ocr_save"),
        name="public_itinerary_ocr_save",
    ),
    path(
        "itinerary/v1/live/<str:token>/cross-sell/",
        dynamic_fb_view("apps.bookings.views.passenger_portal.public_itinerary_cross_sell"),
        name="public_itinerary_cross_sell",
    ),
    # API
    path("api/", include(router.urls)),
    path("api/v1/gds/ingest-pnr/", api_ingest_pnr_view, name="api_gds_ingest_pnr"),
]

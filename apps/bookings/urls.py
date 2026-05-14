from django.urls import path, include
from rest_framework.routers import DefaultRouter


from .views import dashboard_views, report_views, proveedores_views
from apps.cotizaciones import views as cotizaciones_views
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

from core.views.hotel_views import (
    GenerateCopyAPI,
    HotelDetailView,
    HotelListView,
    download_story_view,
)
from core.views.flights_views import FlightSearchView
from core.views.voucher_views import generar_voucher
from apps.marketing.views.marketing_views import GenerateAIImageView, MarketingHubView
from core.views.hotel_api import HotelQuoteAPI

# API ViewSets
from rest_framework import permissions, viewsets, filters
from apps.bookings.models import ProductoServicio
from apps.cotizaciones.views import CotizacionViewSet, ItemCotizacionViewSet
from core.api.mixins.tenant import TenantViewSetMixin
from core.api_registry import get_registered_apis, register_auto_apis

from core.views import cotizaciones_views
from core.views.hotel_views import (
    GenerateCopyAPI,
    HotelDetailView,
    HotelListView,
    download_story_view,
)
from core.views.flights_views import FlightSearchView
from core.views.voucher_views import generar_voucher
from apps.marketing.views.marketing_views import GenerateAIImageView, MarketingHubView
from core.views.hotel_api import HotelQuoteAPI


app_name = 'bookings'

router = DefaultRouter()

class ProductoServicioSerializer(viewsets.ModelViewSet):
    # This is a bit of a hack since the original had classes defined in core/urls.py
    # I should probably import them, but for now I'll just register if I can.
    pass

# We will re-use the registration logic from core/urls.py
try:
    from core.serializers import ProductoServicioSerializer
    class ProductoServicioViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
        queryset = ProductoServicio.objects.filter(activo=True)
        serializer_class = ProductoServicioSerializer
        permission_classes = [permissions.IsAuthenticated]
        filter_backends = [filters.SearchFilter]
        search_fields = ['nombre', 'codigo_interno', 'descripcion']
    
    router.register(r'productoservicio', ProductoServicioViewSet, basename='productoservicio')
    router.register(r'cotizaciones', CotizacionViewSet, basename='cotizaciones')
    router.register(r'items-cotizacion', ItemCotizacionViewSet, basename='items-cotizacion')
except Exception as e:
    print(f"Error registering bookings ViewSets: {e}")

# Automatic Registration (Scoped to Bookings if possible, but core logic is global)
try:
    register_auto_apis()
    registered_apis = get_registered_apis()
    BOOKINGS_MODELS = [
        'AlquilerAutoReserva', 'EventoServicio', 'CircuitoTuristico', 
        'CircuitoDia', 'PaqueteAereo', 'ServicioAdicionalDetalle', 
        'Venta', 'BoletoImportado', 'SegmentoVuelo', 'FeeVenta', 'PagoVenta'
    ]
    for model_class, api_data in registered_apis.items():
        if model_class.__name__ in BOOKINGS_MODELS:
            if api_data['basename'] not in [r[2] for r in router.registry]:
                router.register(api_data['path'], api_data['viewset'], basename=api_data['basename'])
except Exception as e:
    print(f"Error in Bookings Auto API: {e}")


urlpatterns = [
    # Rutas Core heredadas
    path('', include('apps.bookings.urls_core')),
    path('', include('apps.common.urls_core')),

    # Ventas
    path('ventas/', VentaListView.as_view(), name='venta_list'),
    path('ventas/nueva/', VentaCreateView.as_view(), name='venta_create'),
    path('ventas/<int:pk>/', VentaDetailView.as_view(), name='venta_detail'),
    path('ventas/<int:pk>/timeline/', VentaTimelineView.as_view(), name='venta_timeline'),
    path('ventas/<int:pk>/editar/', VentaUpdateView.as_view(), name='venta_update'),
    path('ventas/<int:pk>/eliminar/', VentaDeleteView.as_view(), name='venta_delete'),

    # Proveedores
    path('proveedores/', proveedores_views.ProveedorListView.as_view(), name='proveedor_list'),
    path('proveedores/nuevo/', proveedores_views.ProveedorCreateView.as_view(), name='proveedor_create'),
    path('proveedores/<int:pk>/editar/', proveedores_views.ProveedorUpdateView.as_view(), name='proveedor_update'),
    path('proveedores/<int:pk>/eliminar/', proveedores_views.ProveedorDeleteView.as_view(), name='proveedor_delete'),


    # Inteligencia & Auditoría
    path('auditoria/', RevenueLeakDashboardView.as_view(), name='revenue_leak_dashboard'),
    path('auditoria/<int:pk>/resolver/', resolve_finding_htmx, name='resolve_finding'),

    # HTMX Inline actions for Venta Detail
    path('ventas/<int:venta_pk>/items/agregar/', ItemVentaCreateView.as_view(), name='item_venta_add'),
    path('ventas/items/<int:pk>/editar/', ItemVentaUpdateView.as_view(), name='item_venta_edit'),
    path('ventas/<int:venta_pk>/fees/agregar/', FeeVentaCreateView.as_view(), name='fee_venta_add'),
    path('ventas/<int:venta_pk>/pagos/agregar/', PagoVentaCreateView.as_view(), name='pago_venta_add'),
    # Dashboard de Flujo de Caja
    path('dashboard/', dashboard_main, name='dashboard_main'),
    path('dashboard/stats/', dashboard_stats_htmx, name='dashboard_stats'),
    path('dashboard/whatsapp-qr/', whatsapp_qr_view, name='whatsapp_qr'),
    path('dashboard/whatsapp-pairing/', whatsapp_pairing_code_view, name='whatsapp_pairing'),

    # Cotizaciones
    path('cotizaciones/', cotizaciones_views.CotizacionDashboardView.as_view(), name='cotizacion_dashboard'),
    path('cotizaciones/magic/', cotizaciones_views.MagicQuoterView.as_view(), name='cotizacion_magic'),
    path('cotizaciones/htmx/calcular/', cotizaciones_views.CotizacionHTMXCalculateTotalsView.as_view(), name='cotizacion_htmx_calcular'),
    path('cotizaciones/htmx/add-item/', cotizaciones_views.CotizacionHTMXAddItemView.as_view(), name='cotizacion_htmx_add_item'),
    path('cotizaciones/nueva/', cotizaciones_views.CotizacionCreateView.as_view(), name='cotizacion_nueva'),
    path('cotizaciones/<int:pk>/', cotizaciones_views.CotizacionDetailView.as_view(), name='cotizacion_detalle'),
    path('cotizaciones/<int:pk>/editar/', cotizaciones_views.CotizacionUpdateView.as_view(), name='cotizacion_editar'),
    path('cotizaciones/<int:pk>/cambiar-estado/', cotizaciones_views.CotizacionStatusView.as_view(), name='cotizacion_cambiar_estado'),
    path('cotizaciones/<int:pk>/pdf/', cotizaciones_views.CotizacionPDFView.as_view(), name='cotizacion_pdf'),
    path('cotizaciones/<int:pk>/convertir/', cotizaciones_views.CotizacionConvertirView.as_view(), name='cotizacion_convertir'),
    path('api/cotizaciones/magic-gpt/', cotizaciones_views.MagicQuoterAIView.as_view(), name='cotizacion_magic_gpt'),


    # Hotel Engine & Marketing (Movido de core/urls.py)
    path('hoteles/', HotelListView.as_view(), name='hotel_search'),
    path('hoteles/<slug:slug>/', HotelDetailView.as_view(), name='hotel_detail'),
    path('hoteles/<slug:slug>/story/', download_story_view, name='hotel_story'),
    path('api/marketing/generate-copy/', GenerateCopyAPI.as_view(), name='generate_copy_api'),
    path('api/marketing/generate-image/', GenerateAIImageView.as_view(), name='generate_ai_image'),
    path('marketing/hub/', MarketingHubView.as_view(), name='marketing_hub'),
    path('api/hotels/quote/', HotelQuoteAPI.as_view(), name='hotel_quote_api'),

    # Flight Search (Movido de core/urls.py)
    path('flights/', FlightSearchView.as_view(), name='flight_search'),
    
    # Vouchers
    path('api/ventas/<int:venta_id>/generar-voucher/', generar_voucher, name='generar_voucher'),
    # Vouchers
    path('api/ventas/<int:venta_id>/generar-voucher/', generar_voucher, name='generar_voucher'),

    # API
    path('api/', include(router.urls)),
]
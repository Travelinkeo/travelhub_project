# Contenido del archivo core/urls.py
import json
import logging

from django.http import JsonResponse
from django.urls import include, path, re_path
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from . import views
from .api_registry import register_auto_apis, get_registered_apis
from .chatbot.views import ChatbotConverseView
from .itinerary_generator.views import ItineraryGeneratorView
from .views import (
    ActividadServicioViewSet,
    AirTicketsEditableListView,
    AlojamientoReservaViewSet,
    AlquilerAutoReservaViewSet,
    AsientoContableViewSet,
    BoletoImportadoListView,
    BoletoImportadoViewSet,
    BoletoManualEntryView,
    BoletoUploadAPIView,
    CiudadViewSet,
    CircuitoDiaViewSet,
    CircuitoTuristicoViewSet,
    EventoServicioViewSet,
    FacturaViewSet,
    FeeVentaViewSet,
    HealthCheckView,
    HomeView,
    LoginView,
    MonedaViewSet,
    PaginaCMSDetailView,
    PagoVentaViewSet,
    PaisViewSet,
    PaqueteAereoViewSet,
    PaqueteCMSListView,
    ProductoServicioViewSet,
    ProveedorViewSet,
    SalesSummaryView,
    SegmentoVueloViewSet,
    ServicioAdicionalDetalleViewSet,
    TipoCambioViewSet,
    TrasladoServicioViewSet,
    VentaParseMetadataViewSet,
    VentaViewSet,
)
from personas.views import ClienteViewSet, PasajeroViewSet


@method_decorator(csrf_exempt, name='dispatch')
class TokenLogoutView(View):
    def post(self, request, *args, **kwargs):
        try:
            import json
            body = json.loads(request.body or '{}')
            refresh = body.get('refresh')
            if not refresh:
                return JsonResponse({'detail': 'Missing refresh token'}, status=400)
            token = RefreshToken(refresh)
            token.blacklist()
            return JsonResponse({'detail': 'Logged out'}, status=205)
        except Exception as e:
            return JsonResponse({'detail': str(e)}, status=400)

@csrf_exempt
@require_POST
def csp_report_view(request):
    try:
        data = json.loads(request.body or '{}')
        logger = __import__('logging').getLogger('csp')
        logger.warning('CSP violation report: %s', data)
    except Exception as e:
        return JsonResponse({'detail': str(e)}, status=400)
    return JsonResponse({'detail': 'received'}, status=202)

router = DefaultRouter()

# Registrar APIs automáticas para modelos en admin
register_auto_apis()
apis = get_registered_apis()
for model, api_data in apis.items():
    model_name = model._meta.model_name
    # Evitar conflictos con APIs existentes
    existing_basenames = ['venta', 'factura', 'asientocontable', 'segmento-vuelo', 'alojamiento-reserva', 'traslado-servicio', 'actividad-servicio', 'fee-venta', 'pago-venta', 'venta-metadata', 'alquiler-auto', 'evento-servicio', 'circuito-turistico', 'circuito-dia', 'paquete-aereo', 'servicio-adicional-detalle', 'cliente', 'pasajero', 'proveedor', 'ciudad', 'moneda', 'pais']
    if model_name not in existing_basenames and model.__name__ != 'BoletoImportado':
        try:
            prefix = api_data['basename']
            router.register(prefix, api_data['viewset'], basename=api_data['basename'])
            print(f"API automática registrada para {model.__name__} en /{prefix}/")
            print(f"ViewSet: {api_data['viewset']}")
        except Exception as e:
            print(f"Error registrando API automática para {model.__name__}: {e}")
router.register(r'ventas', VentaViewSet, basename='venta')
router.register(r'facturas', FacturaViewSet, basename='factura')
router.register(r'asientoscontables', AsientoContableViewSet, basename='asientocontable')
router.register(r'segmentos-vuelo', SegmentoVueloViewSet, basename='segmento-vuelo')
router.register(r'alojamientos', AlojamientoReservaViewSet, basename='alojamiento-reserva')
router.register(r'traslados', TrasladoServicioViewSet, basename='traslado-servicio')
router.register(r'actividades', ActividadServicioViewSet, basename='actividad-servicio')
router.register(r'fees-venta', FeeVentaViewSet, basename='fee-venta')
router.register(r'pagos-venta', PagoVentaViewSet, basename='pago-venta')
router.register(r'ventas-metadata', VentaParseMetadataViewSet, basename='venta-metadata')
router.register(r'alquileres-autos', AlquilerAutoReservaViewSet, basename='alquiler-auto')
router.register(r'eventos-servicios', EventoServicioViewSet, basename='evento-servicio')
router.register(r'circuitos-turisticos', CircuitoTuristicoViewSet, basename='circuito-turistico')
router.register(r'circuitos-dias', CircuitoDiaViewSet, basename='circuito-dia')
router.register(r'paquetes-aereos', PaqueteAereoViewSet, basename='paquete-aereo')
router.register(r'servicios-adicionales', ServicioAdicionalDetalleViewSet, basename='servicio-adicional-detalle')
router.register(r'boletos-importados', BoletoImportadoViewSet, basename='boletos-importados')
router.register(r'ciudades', CiudadViewSet, basename='ciudad')
router.register(r'monedas', MonedaViewSet, basename='moneda')
router.register(r'paises', PaisViewSet, basename='pais')
router.register(r'tipos-cambio', TipoCambioViewSet, basename='tipo-cambio')
router.register(r'clientes', ClienteViewSet, basename='cliente')
router.register(r'pasajeros', PasajeroViewSet, basename='pasajero')
router.register(r'proveedores', ProveedorViewSet, basename='proveedor')
router.register(r'productos-servicio', views.ProductoServicioViewSet, basename='producto-servicio')

# Importar y registrar cotizaciones
from cotizaciones.views import CotizacionViewSet, ItemCotizacionViewSet
router.register(r'cotizaciones', CotizacionViewSet, basename='cotizaciones')
router.register(r'items-cotizacion', ItemCotizacionViewSet, basename='items-cotizacion')

print(f"Total URLs en router: {len(router.urls)}")

app_name = 'core'

urlpatterns = [
    path('api/boletos/upload/', BoletoUploadAPIView.as_view(), name='api_boleto_upload'),
    path('api/itineraries/generate/', ItineraryGeneratorView.as_view(), name='itinerary_generator'),
    path('api/chatbot/converse/', ChatbotConverseView.as_view(), name='chatbot_converse'),
    path('api/health/', HealthCheckView.as_view(), name='health'),
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/jwt/obtain/', TokenObtainPairView.as_view(), name='jwt_obtain_pair'),
    path('api/auth/jwt/refresh/', TokenRefreshView.as_view(), name='jwt_refresh'),
    path('api/auth/jwt/verify/', TokenVerifyView.as_view(), name='jwt_verify'),
    path('api/auth/jwt/logout/', TokenLogoutView.as_view(), name='jwt_logout'),
    path('api/dashboard/stats/', views.dashboard_stats_api, name='dashboard_stats'),
    path('csp-report/', csp_report_view, name='csp_report'),
    path('api/', include(router.urls)),
    path('core/api/', include((router.urls, 'core'), namespace='core-api-alias')),
    path('', HomeView.as_view(), name='home'),
    path('pagina/<slug:slug>/', PaginaCMSDetailView.as_view(), name='pagina_cms_detalle'),
    path('paquetes/', PaqueteCMSListView.as_view(), name='lista_paquetes_cms'),
    path('dashboard/boletos/', BoletoImportadoListView.as_view(), name='dashboard_boletos'),
    path('boletos/manual/entrada/', BoletoManualEntryView.as_view(), name='manual_ticket_entry'),
    path('boletos/upload/', views.upload_boleto_file, name='upload_boleto_file'),
    path('boletos/eliminar/<int:pk>/', views.delete_boleto_importado, name='delete_boleto_importado'),
    path('dashboard/ventas/resumen/', SalesSummaryView.as_view(), name='dashboard_resumen_ventas'),
    path('dashboard/ventas/boletos-aereos/', AirTicketsEditableListView.as_view(), name='air_tickets_editable'),
]

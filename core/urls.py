# Contenido del archivo core/urls.py
import json

from django.http import JsonResponse
from django.urls import include, path
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
from .chatbot.views import ChatbotConverseView
from .itinerary_generator.views import ItineraryGeneratorView
from .views import (
    ActividadServicioViewSet,
    AirTicketsEditableListView,
    AlojamientoReservaViewSet,
    AlquilerAutoReservaViewSet,
    AsientoContableViewSet,
    BoletoImportadoListView,
    BoletoManualEntryView,
    BoletoUploadAPIView, # AÑADIDO AQUÍ
    CircuitoDiaViewSet,
    CircuitoTuristicoViewSet,
    EventoServicioViewSet,
    FacturaViewSet,
    FeeVentaViewSet,
    HealthCheckView,
    HomeView,
    LoginView,
    PaginaCMSDetailView,
    PagoVentaViewSet,
    PaqueteAereoViewSet,
    PaqueteCMSListView,
    SalesSummaryView,
    SegmentoVueloViewSet,
    ServicioAdicionalDetalleViewSet,
    TrasladoServicioViewSet,
    VentaParseMetadataViewSet,
    VentaViewSet,
)


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
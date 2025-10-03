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

from .views.passport_views import upload_passport, create_client_from_passport
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

# Registro manual de APIs básicas
from rest_framework import viewsets, permissions, filters
from .serializers import PaisSerializer, CiudadSerializer, MonedaSerializer, TipoCambioSerializer, ProductoServicioSerializer
from .models_catalogos import Pais, Ciudad, Moneda, TipoCambio, ProductoServicio

class PaisViewSet(viewsets.ModelViewSet):
    queryset = Pais.objects.all()
    serializer_class = PaisSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'codigo_iso_2', 'codigo_iso_3']

class CiudadViewSet(viewsets.ModelViewSet):
    queryset = Ciudad.objects.all()
    serializer_class = CiudadSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'pais__nombre', 'region_estado']

class MonedaViewSet(viewsets.ModelViewSet):
    queryset = Moneda.objects.all()
    serializer_class = MonedaSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'codigo_iso']

class TipoCambioViewSet(viewsets.ModelViewSet):
    queryset = TipoCambio.objects.all()
    serializer_class = TipoCambioSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

class ProductoServicioViewSet(viewsets.ModelViewSet):
    queryset = ProductoServicio.objects.filter(activo=True)
    serializer_class = ProductoServicioSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'codigo_interno', 'descripcion']

router.register(r'paises', PaisViewSet, basename='pais')
router.register(r'ciudades', CiudadViewSet, basename='ciudad')
router.register(r'monedas', MonedaViewSet, basename='moneda')
router.register(r'tipos-cambio', TipoCambioViewSet, basename='tipocambio')
router.register(r'clientes', ClienteViewSet, basename='cliente')
router.register(r'pasajeros', PasajeroViewSet, basename='pasajero')

# Register ViewSets from views.py
try:
    from .views import (
        ProveedorViewSet, VentaViewSet, FacturaViewSet, AsientoContableViewSet,
        SegmentoVueloViewSet, AlojamientoReservaViewSet, TrasladoServicioViewSet,
        ActividadServicioViewSet, FeeVentaViewSet, PagoVentaViewSet,
        VentaParseMetadataViewSet, AlquilerAutoReservaViewSet, EventoServicioViewSet,
        CircuitoTuristicoViewSet, CircuitoDiaViewSet, PaqueteAereoViewSet,
        ServicioAdicionalDetalleViewSet, BoletoImportadoViewSet, AuditLogViewSet
    )
    router.register(r'proveedores', ProveedorViewSet, basename='proveedor')
    router.register(r'ventas', VentaViewSet, basename='venta')
    router.register(r'facturas', FacturaViewSet, basename='factura')
    router.register(r'asientos-contables', AsientoContableViewSet, basename='asiento-contable')
    router.register(r'segmentos-vuelo', SegmentoVueloViewSet, basename='segmento-vuelo')
    router.register(r'alojamientos', AlojamientoReservaViewSet, basename='alojamiento')
    router.register(r'traslados', TrasladoServicioViewSet, basename='traslado')
    router.register(r'actividades', ActividadServicioViewSet, basename='actividad')
    router.register(r'fees-venta', FeeVentaViewSet, basename='fee-venta')
    router.register(r'pagos-venta', PagoVentaViewSet, basename='pago-venta')
    router.register(r'ventas-metadata', VentaParseMetadataViewSet, basename='venta-metadata')
    router.register(r'alquileres-autos', AlquilerAutoReservaViewSet, basename='alquiler-auto')
    router.register(r'eventos-servicios', EventoServicioViewSet, basename='evento-servicio')
    router.register(r'circuitos-turisticos', CircuitoTuristicoViewSet, basename='circuito-turistico')
    router.register(r'circuitos-dias', CircuitoDiaViewSet, basename='circuito-dia')
    router.register(r'paquetes-aereos', PaqueteAereoViewSet, basename='paquete-aereo')
    router.register(r'servicios-adicionales', ServicioAdicionalDetalleViewSet, basename='servicio-adicional')
    router.register(r'boletos-importados', BoletoImportadoViewSet, basename='boleto-importado')
    router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')
    print("All ViewSets registered successfully")
except Exception as e:
    print(f"Error registering ViewSets: {e}")

# Manually register moneda API with search functionality
# try:
#     from .views import MonedaViewSet
#     router.register(r'monedas', MonedaViewSet, basename='monedas')
#     print("Monedas API registered manually with search functionality")
# except ImportError as e:
#     print(f"Could not import MonedaViewSet: {e}")
router.register(r'productoservicio', ProductoServicioViewSet, basename='productoservicio')

# Importar y registrar cotizaciones
from cotizaciones.views import CotizacionViewSet, ItemCotizacionViewSet
router.register(r'cotizaciones', CotizacionViewSet, basename='cotizaciones')
router.register(r'items-cotizacion', ItemCotizacionViewSet, basename='items-cotizacion')

print(f"Total URLs en router: {len(router.urls)}")

app_name = 'core'

urlpatterns = [
    # Temporarily commented out to fix server startup
    # path('api/boletos/upload/', views.BoletoUploadAPIView.as_view(), name='api_boleto_upload'),
    # path('api/itineraries/generate/', views.ItineraryGeneratorView.as_view(), name='itinerary_generator'),
    # path('api/chatbot/converse/', views.ChatbotConverseView.as_view(), name='chatbot_converse'),
    # path('api/health/', views.HealthCheckView.as_view(), name='health'),
    # path('api/auth/login/', views.LoginView.as_view(), name='login'),
    path('api/auth/jwt/obtain/', TokenObtainPairView.as_view(), name='jwt_obtain_pair'),
    path('api/auth/jwt/refresh/', TokenRefreshView.as_view(), name='jwt_refresh'),
    path('api/auth/jwt/verify/', TokenVerifyView.as_view(), name='jwt_verify'),
    path('api/auth/jwt/logout/', TokenLogoutView.as_view(), name='jwt_logout'),
    # path('api/dashboard/stats/', views.dashboard_stats_api, name='dashboard_stats'),
    # path('api/ai-agent/chat/', views.ai_agent_chat, name='ai_agent_chat'),
    path('csp-report/', csp_report_view, name='csp_report'),
    path('api/', include(router.urls)),
    path('core/api/', include((router.urls, 'core'), namespace='core-api-alias')),
    # path('', views.HomeView.as_view(), name='home'),
    # path('pagina/<slug:slug>/', views.PaginaCMSDetailView.as_view(), name='pagina_cms_detalle'),
    # path('paquetes/', views.PaqueteCMSListView.as_view(), name='lista_paquetes_cms'),
    # path('dashboard/boletos/', views.BoletoImportadoListView.as_view(), name='dashboard_boletos'),
    # path('boletos/manual/entrada/', views.BoletoManualEntryView.as_view(), name='manual_ticket_entry'),
    # path('boletos/upload/', views.upload_boleto_file, name='upload_boleto_file'),
    # path('boletos/eliminar/<int:pk>/', views.delete_boleto_importado, name='delete_boleto_importado'),
    # path('dashboard/ventas/resumen/', views.SalesSummaryView.as_view(), name='dashboard_resumen_ventas'),
    # path('dashboard/ventas/boletos-aereos/', views.AirTicketsEditableListView.as_view(), name='air_tickets_editable'),
    # Passport OCR endpoints
    path('api/passport/upload/', upload_passport, name='passport_upload'),
    path('api/passport/<int:passport_id>/create-client/', create_client_from_passport, name='create_client_from_passport'),
]

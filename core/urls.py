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
from .views.home_view import HomeView

try:
    from .views import dashboard_stats_api
except ImportError:
    dashboard_stats_api = None


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
from .serializers import PaisSerializer, CiudadSerializer, MonedaSerializer, TipoCambioSerializer, ProductoServicioSerializer, AerolineaSerializer
from .models_catalogos import Pais, Ciudad, Moneda, TipoCambio, ProductoServicio, Aerolinea

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

class AerolineaViewSet(viewsets.ModelViewSet):
    queryset = Aerolinea.objects.filter(activa=True)
    serializer_class = AerolineaSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'codigo_iata']

router.register(r'paises', PaisViewSet, basename='pais')
router.register(r'ciudades', CiudadViewSet, basename='ciudad')
router.register(r'monedas', MonedaViewSet, basename='moneda')
router.register(r'tipos-cambio', TipoCambioViewSet, basename='tipocambio')
router.register(r'aerolineas', AerolineaViewSet, basename='aerolinea')
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

# Register Liquidaciones ViewSet
try:
    from .views.liquidacion_views import LiquidacionProveedorViewSet, ItemLiquidacionViewSet
    router.register(r'liquidaciones', LiquidacionProveedorViewSet, basename='liquidacion')
    router.register(r'items-liquidacion', ItemLiquidacionViewSet, basename='item-liquidacion')
    print("Liquidaciones ViewSets registered successfully")
except Exception as e:
    print(f"Error registering Liquidaciones ViewSets: {e}")

# Register Pasaportes ViewSet
try:
    from .views.pasaporte_api_views import PasaporteEscaneadoViewSet
    router.register(r'pasaportes', PasaporteEscaneadoViewSet, basename='pasaporte')
    print("Pasaportes ViewSet registered successfully")
except Exception as e:
    print(f"Error registering Pasaportes ViewSet: {e}")

# Register Comunicaciones ViewSet
try:
    from .views.comunicaciones_views import ComunicacionProveedorViewSet
    router.register(r'comunicaciones', ComunicacionProveedorViewSet, basename='comunicacion')
    print("Comunicaciones ViewSet registered successfully")
except Exception as e:
    print(f"Error registering Comunicaciones ViewSet: {e}")

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
    path(r'api/auth/jwt/obtain/', TokenObtainPairView.as_view(), name='jwt_obtain_pair'),
    path(r'api/auth/jwt/refresh/', TokenRefreshView.as_view(), name='jwt_refresh'),
    path(r'api/auth/jwt/verify/', TokenVerifyView.as_view(), name='jwt_verify'),
    path(r'api/auth/jwt/logout/', TokenLogoutView.as_view(), name='jwt_logout'),
    path(r'api/dashboard/stats/', dashboard_stats_api, name='dashboard_stats') if dashboard_stats_api else path(r'api/dashboard/stats/', lambda r: JsonResponse({'error': 'Not available'}, status=404)),
    path(r'csp-report/', csp_report_view, name='csp_report'),
    path(r'api/', include(router.urls)),
    path(r'core/api/', include((router.urls, 'core'), namespace='core-api-alias')),
    
    # Translator APIs
    path(r'api/translator/', include('core.translator_urls', namespace='translator')),
    
    # Chatbot APIs
    path('api/chatbot/', include('core.chatbot.urls', namespace='chatbot')),
    
    path('', HomeView.as_view(), name='home'),
    # path('pagina/<slug:slug>/', views.PaginaCMSDetailView.as_view(), name='pagina_cms_detalle'),
    # path('paquetes/', views.PaqueteCMSListView.as_view(), name='lista_paquetes_cms'),
    # path('dashboard/boletos/', views.BoletoImportadoListView.as_view(), name='dashboard_boletos'),
    # path('boletos/manual/entrada/', views.BoletoManualEntryView.as_view(), name='manual_ticket_entry'),
    # path('boletos/upload/', views.upload_boleto_file, name='upload_boleto_file'),
    # path('boletos/eliminar/<int:pk>/', views.delete_boleto_importado, name='delete_boleto_importado'),
    # path('dashboard/ventas/resumen/', views.SalesSummaryView.as_view(), name='dashboard_resumen_ventas'),
    # path('dashboard/ventas/boletos-aereos/', views.AirTicketsEditableListView.as_view(), name='air_tickets_editable'),
    # Passport OCR endpoints
    path(r'api/passport/upload/', upload_passport, name='passport_upload'),
    path(r'api/passport/<int:passport_id>/create-client/', create_client_from_passport, name='create_client_from_passport'),
    
    # API de ventas de boletos para Next.js
    path(r'api/ventas-boletos/', lambda r: __import__('core.views.dashboard_boletos', fromlist=['ventas_boletos_api']).ventas_boletos_api(r), name='ventas_boletos_api'),
    path(r'dashboard/ventas-boletos/', lambda r: __import__('core.views.dashboard_boletos', fromlist=['dashboard_boletos_html']).dashboard_boletos_html(r), name='dashboard_ventas_boletos'),
    path(r'api/boletos/actualizar-item/', lambda r: __import__('core.views.dashboard_boletos', fromlist=['actualizar_item_boleto']).actualizar_item_boleto(r), name='actualizar_item_boleto'),
    
    # Dashboard y Vouchers
    path(r'api/dashboard/metricas/', lambda r: __import__('core.views.dashboard_views', fromlist=['dashboard_metricas']).dashboard_metricas(r), name='dashboard_metricas'),
    path(r'api/dashboard/alertas/', lambda r: __import__('core.views.dashboard_views', fromlist=['dashboard_alertas']).dashboard_alertas(r), name='dashboard_alertas'),
    path(r'api/ventas/<int:venta_id>/generar-voucher/', lambda r, venta_id: __import__('core.views.voucher_views', fromlist=['generar_voucher']).generar_voucher(r, venta_id), name='generar_voucher'),
    
    # Auditoría
    path(r'api/auditoria/venta/<int:venta_id>/', lambda r, venta_id: __import__('core.views.auditoria_views', fromlist=['historial_venta']).historial_venta(r, venta_id), name='historial_venta'),
    path(r'api/auditoria/estadisticas/', lambda r: __import__('core.views.auditoria_views', fromlist=['estadisticas_auditoria']).estadisticas_auditoria(r), name='estadisticas_auditoria'),
    
    # Boletos
    path(r'api/boletos/sin-venta/', lambda r: __import__('core.views.boleto_api_views', fromlist=['boletos_sin_venta']).boletos_sin_venta(r), name='boletos_sin_venta'),
    path(r'api/boletos/<int:boleto_id>/reintentar-parseo/', lambda r, boleto_id: __import__('core.views.boleto_api_views', fromlist=['reintentar_parseo']).reintentar_parseo(r, boleto_id), name='reintentar_parseo'),
    path(r'api/boletos/<int:boleto_id>/crear-venta/', lambda r, boleto_id: __import__('core.views.boleto_api_views', fromlist=['crear_venta_desde_boleto']).crear_venta_desde_boleto(r, boleto_id), name='crear_venta_desde_boleto'),
    
    # Reportes Contables
    path(r'api/reportes/libro-diario/', lambda r: __import__('core.views.reportes_views', fromlist=['libro_diario']).libro_diario(r), name='libro_diario'),
    path(r'api/reportes/balance-comprobacion/', lambda r: __import__('core.views.reportes_views', fromlist=['balance_comprobacion']).balance_comprobacion(r), name='balance_comprobacion'),
    path(r'api/reportes/validar-cuadre/', lambda r: __import__('core.views.reportes_views', fromlist=['validar_cuadre']).validar_cuadre(r), name='validar_cuadre'),
    path(r'api/reportes/exportar-excel/', lambda r: __import__('core.views.reportes_views', fromlist=['exportar_excel']).exportar_excel(r), name='exportar_excel'),
    
    # OpenAPI/Swagger Documentation
    path(r'api/schema/', lambda r: __import__('drf_spectacular.views', fromlist=['SpectacularAPIView']).SpectacularAPIView.as_view(), name='schema'),
    path(r'api/docs/', lambda r: __import__('drf_spectacular.views', fromlist=['SpectacularSwaggerView']).SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path(r'api/redoc/', lambda r: __import__('drf_spectacular.views', fromlist=['SpectacularRedocView']).SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Contenido del archivo core/urls.py
from django.http import HttpResponse

def debug_check(request):
    return HttpResponse("SYSTEM DIAGNOSTIC: travelhub_project/core IS LIVE")

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

# Importar desde el paquete de vistas modular
from .views import (
    erp_views, ventas_views, proveedores_views, clientes_views, agencia_views, facturacion_views,
    passport_views, home_view, pasajeros_views, user_profile_views, flights_views, catalogos_views, audit_views_frontend,
    inventario_views
)
from .dashboard_stats import get_dashboard_stats as dashboard_stats_api
from .api.hotel_api import HotelQuoteAPI
from core.views.hotel_views import HotelListView, HotelDetailView, download_story_view, GenerateCopyAPI
from core.views.marketing_views import GenerateAIImageView, MarketingHubView
from apps.crm.api import ClienteViewSet, PasajeroViewSet

# Alias para compatibilidad (Importando directamente del legacy para evitar ciclos)
from core.views.boleto_views import (
    BoletoUploadAPIView,
    BoletoMassActionAPIView,
    VentaDoubleInvoiceAPIView,
    BoletoRetryParseAPIView,
    BoletoAuditAPIView,
    BoletoDeleteAPIView
)
from core.views.intelligence_views import GDSAnalyzerView, GDSAnalysisAjaxView, GDSInjectERPView
from core.views.audit_views import AuditLogListView
from core.views_legacy import (
    HomeView, 
    upload_boleto_file
)
from core.views.ocr_views import OCRPassportView
from core.views.id_scanner_views import CedulaScannerAPIView
from core.views.settings_views import BrandingSettingsView
from core.views.onboarding_views import SaaSOnboardingView
from core.views.notifications import notificaciones_live_view


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
    pagination_class = None
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'codigo_iso_2', 'codigo_iso_3']

class CiudadViewSet(viewsets.ModelViewSet):
    queryset = Ciudad.objects.all()
    serializer_class = CiudadSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    pagination_class = None
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
    from core.views_legacy import (
        ProveedorViewSet, VentaViewSet, FacturaViewSet, AsientoContableViewSet,
        SegmentoVueloViewSet, AlojamientoReservaViewSet, TrasladoServicioViewSet,
        ActividadServicioViewSet, FeeVentaViewSet, PagoVentaViewSet,
        VentaParseMetadataViewSet, AlquilerAutoReservaViewSet, EventoServicioViewSet,
        CircuitoTuristicoViewSet, CircuitoDiaViewSet, PaqueteAereoViewSet,
        ServicioAdicionalDetalleViewSet, BoletoImportadoViewSet, AuditLogViewSet
    )
# ViewSets registered with the router are mostly legacy/Next.js dependencies.
# We comment them out to ensure they are no longer exposed, while keeping record.
# router.register(r'proveedores', ProveedorViewSet, basename='proveedor')
# router.register(r'ventas', VentaViewSet, basename='venta')
# router.register(r'facturas', FacturaViewSet, basename='factura')
# router.register(r'asientos-contables', AsientoContableViewSet, basename='asiento-contable')
# router.register(r'segmentos-vuelo', SegmentoVueloViewSet, basename='segmento-vuelo')
# router.register(r'alojamientos', AlojamientoReservaViewSet, basename='alojamiento')
# router.register(r'traslados', TrasladoServicioViewSet, basename='traslado')
# router.register(r'actividades', ActividadServicioViewSet, basename='actividad')
# router.register(r'fees-venta', FeeVentaViewSet, basename='fee-venta')
# router.register(r'pagos-venta', PagoVentaViewSet, basename='pago-venta')
# router.register(r'ventas-metadata', VentaParseMetadataViewSet, basename='venta-metadata')
# router.register(r'alquileres-autos', AlquilerAutoReservaViewSet, basename='alquiler-auto')
# router.register(r'eventos-servicios', EventoServicioViewSet, basename='evento-servicio')
# router.register(r'circuitos-turisticos', CircuitoTuristicoViewSet, basename='circuito-turistico')
# router.register(r'circuitos-dias', CircuitoDiaViewSet, basename='circuito-dia')
# router.register(r'paquetes-aereos', PaqueteAereoViewSet, basename='paquete-aereo')
# router.register(r'servicios-adicionales', ServicioAdicionalDetalleViewSet, basename='servicio-adicional')
# router.register(r'boletos-importados', BoletoImportadoViewSet, basename='boleto-importado')
# router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')
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

# Register Pasaportes ViewSet (Commented out because PasaporteEscaneado model is missing)
# try:
#     from .views.pasaporte_api_views import PasaporteEscaneadoViewSet
#     router.register(r'pasaportes', PasaporteEscaneadoViewSet, basename='pasaporte')
#     print("Pasaportes ViewSet registered successfully")
# except Exception as e:
#     print(f"Error registering Pasaportes ViewSet: {e}")

# Register Comunicaciones ViewSet
# try:
#     from .views.comunicaciones_views import ComunicacionProveedorViewSet
#     router.register(r'comunicaciones', ComunicacionProveedorViewSet, basename='comunicacion')
#     print("Comunicaciones ViewSet registered successfully")
# except Exception as e:
#     print(f"Error registering Comunicaciones ViewSet: {e}")

# Register Agencia ViewSet
try:
    # from .views.agencia_views import AgenciaViewSet, UsuarioAgenciaViewSet
    # router.register(r'agencias', AgenciaViewSet, basename='agencia')
    # router.register(r'usuarios-agencia', UsuarioAgenciaViewSet, basename='usuario-agencia')
    print("Agencia ViewSets registered successfully")
except Exception as e:
    print(f"Error registering Agencia ViewSets: {e}")
    import traceback
    traceback.print_exc()

# Manually register moneda API with search functionality
# try:
#     from .views import MonedaViewSet
#     router.register(r'monedas', MonedaViewSet, basename='monedas')
#     print("Monedas API registered manually with search functionality")
# except ImportError as e:
#     print(f"Could not import MonedaViewSet: {e}")
router.register(r'productoservicio', ProductoServicioViewSet, basename='productoservicio')


# Importar y registrar cotizaciones
from core.views import cotizaciones_views
from apps.cotizaciones.views import CotizacionViewSet, ItemCotizacionViewSet
from core.views.catalogos_api import ComisionProveedorServicioViewSet

router.register(r'cotizaciones', CotizacionViewSet, basename='cotizaciones')
router.register(r'items-cotizacion', ItemCotizacionViewSet, basename='items-cotizacion')
router.register(r'comisiones', ComisionProveedorServicioViewSet, basename='comisiones')

# Register Facturas Consolidadas ViewSet
try:
    from .views.factura_consolidada_views import FacturaConsolidadaViewSet, ItemFacturaConsolidadaViewSet
    router.register(r'facturas-consolidadas', FacturaConsolidadaViewSet, basename='factura-consolidada')
    router.register(r'items-factura-consolidada', ItemFacturaConsolidadaViewSet, basename='item-factura-consolidada')
    print("Facturas Consolidadas ViewSets registered successfully")
except Exception as e:
    print(f"Error registering Facturas Consolidadas ViewSets: {e}")

# Register Libro de Ventas ViewSet
try:
    from .views.libro_ventas_views import LibroVentasViewSet
    router.register(r'libro-ventas', LibroVentasViewSet, basename='libro-ventas')
    print("Libro de Ventas ViewSet registered successfully")
except Exception as e:
    print(f"Error registering Libro de Ventas ViewSet: {e}")

# Register Tarifario Hoteles ViewSets
try:
    from .views.tarifario_views import TarifarioProveedorViewSet, HotelTarifarioViewSet
    router.register(r'tarifarios', TarifarioProveedorViewSet, basename='tarifario')
    router.register(r'hoteles-tarifario', HotelTarifarioViewSet, basename='hotel-tarifario')
    print("Tarifario Hoteles ViewSets registered successfully")
except Exception as e:
    print(f"Error registering Tarifario Hoteles ViewSets: {e}")

# Register Mejoras de Boletería ViewSets (Commented out because HistorialCambioBoleto and AnulacionBoleto models are missing)
# try:
#     from .views.boletos_mejoras_views import HistorialCambioBoletoViewSet, AnulacionBoletoViewSet
#     router.register(r'historial-cambios-boletos', HistorialCambioBoletoViewSet, basename='historial-cambio-boleto')
#     router.register(r'anulaciones-boletos', AnulacionBoletoViewSet, basename='anulacion-boleto')
#     print("Mejoras de Boletería ViewSets registered successfully")
# except Exception as e:
#     print(f"Error registering Mejoras de Boletería ViewSets: {e}")

print(f"Total URLs en router: {len(router.urls)}")

app_name = 'core'

from django.views.generic import RedirectView
from core.views.flights_views import FlightSearchView
from core.views.telegram_views import flyer_mini_app_view, generate_flyer_api

urlpatterns = [
    # SaaS Onboarding (Público)
    path('onboarding/', SaaSOnboardingView.as_view(), name='onboarding_start'),

    # Telegram Mini Apps
    path('telegram/flyer-app/', flyer_mini_app_view, name='telegram_flyer_app'),
    path('api/generate-flyer/', generate_flyer_api, name='api_generate_flyer'),

    # Tasas de Cambio y Catálogos
    path('setup/catalogos/', catalogos_views.CatalogosCenterView.as_view(), name='catalogos_center'),
    path('setup/catalogos/aerolineas/', catalogos_views.AerolineaListView.as_view(), name='aerolineas_list'),
    path('setup/catalogos/productos/', catalogos_views.ProductoServicioListView.as_view(), name='productos_list'),
    path('setup/catalogos/geografia/', catalogos_views.GeografiaListView.as_view(), name='geografia_list'),
    
    # Catálogo Terrestre (Inventario Propio)
    path('inventario/terrestre/', inventario_views.CatalogoTerrestreListView.as_view(), name='catalogo_terrestre'),
    path('inventario/terrestre/nuevo/', inventario_views.ProductoTerrestreCreateView.as_view(), name='producto_terrestre_create'),
    
    # Proveedores
    path('setup/catalogos/proveedores/', catalogos_views.ProveedorListView.as_view(), name='proveedores_list'),
    path('setup/catalogos/proveedores/nuevo/', catalogos_views.ProveedorCreateView.as_view(), name='proveedores_nuevo'),
    path('setup/catalogos/proveedores/<int:pk>/editar/', catalogos_views.ProveedorUpdateView.as_view(), name='proveedores_editar'),
    path('setup/catalogos/proveedores/<int:pk>/eliminar/', catalogos_views.ProveedorDeleteView.as_view(), name='proveedores_eliminar'),
    
    # Comisiones
    path('setup/catalogos/comisiones/', catalogos_views.ComisionProveedorServicioListView.as_view(), name='comisiones_list'),
    path('setup/catalogos/comisiones/nuevo/', catalogos_views.ComisionProveedorServicioCreateView.as_view(), name='comisiones_nuevo'),
    path('setup/catalogos/comisiones/<int:pk>/editar/', catalogos_views.ComisionProveedorServicioUpdateView.as_view(), name='comisiones_editar'),
    path('setup/catalogos/comisiones/<int:pk>/eliminar/', catalogos_views.ComisionProveedorServicioDeleteView.as_view(), name='comisiones_eliminar'),
    path('setup/tasas/', catalogos_views.TipoCambioListView.as_view(), name='tasas_list'),
    path('setup/tasas/nueva/', catalogos_views.TipoCambioCreateView.as_view(), name='tasas_nuevo'),
    path('setup/tasas/sincronizar/', catalogos_views.SincronizarTasasActionView.as_view(), name='tasas_sincronizar'),
    
    # Stripe Billing Success/Cancel
    path('billing/success/', lambda r: __import__('core.views.billing_success_views', fromlist=['billing_success']).billing_success(r), name='billing_success'),
    path('billing/cancel/', lambda r: __import__('core.views.billing_success_views', fromlist=['billing_cancel']).billing_cancel(r), name='billing_cancel'),
    
    # Flight Search
    path('flights/', FlightSearchView.as_view(), name='flight_search'),
    # Redirects
    path('', RedirectView.as_view(pattern_name='core:modern_dashboard', permanent=False), name='home'),
    path('dashboard/', RedirectView.as_view(pattern_name='core:modern_dashboard', permanent=False), name='dashboard_root'),

    # 🚀 REAL TIME AUTOMATION (Magic Toasts)
    
    path('api/boletos/upload/', BoletoUploadAPIView.as_view(), name='api_boleto_upload'),
    path('api/boletos/<int:pk>/delete/', BoletoDeleteAPIView.as_view(), name='api_boleto_delete'),
    # path('api/itineraries/generate/', views.ItineraryGeneratorView.as_view(), name='itinerary_generator'),
    path('upload/boleto/', lambda r: __import__('core.views.upload', fromlist=['UploadBoletoView']).UploadBoletoView.as_view()(r), name='upload_boleto'),
    path('upload/boleto/<int:pk>/revisar/', lambda r, pk: __import__('core.views.upload', fromlist=['ReviewBoletoView']).ReviewBoletoView.as_view()(r, pk=pk), name='revisar_boleto'),
    path('upload/boleto/<int:pk>/desasociar-venta/', lambda r, pk: __import__('core.views.upload', fromlist=['DesasociarVentaView']).DesasociarVentaView.as_view()(r, pk=pk), name='desasociar_venta'),
    path('upload/boleto/<int:pk>/eliminar-fisicamente/', lambda r, pk: __import__('core.views.upload', fromlist=['eliminar_boleto']).eliminar_boleto(r, pk=pk), name='eliminar_boleto_hard'),
    path('ventas/<int:pk>/eliminar-fisicamente/', lambda r, pk: __import__('core.views.ventas_views', fromlist=['eliminar_venta']).eliminar_venta(r, pk=pk), name='eliminar_venta_hard'),
    # path('api/chatbot/converse/', views.ChatbotConverseView.as_view(), name='chatbot_converse'),
    # path('api/health/', views.HealthCheckView.as_view(), name='health'),
    # path('api/auth/login/', views.LoginView.as_view(), name='login'),
    path(r'api/auth/jwt/obtain/', TokenObtainPairView.as_view(), name='jwt_obtain_pair'),
    path('dashboard/erp/boletos/', erp_views.DashboardBoletosView.as_view(), name='boletos_dashboard'),
    path('dashboard/erp/boletos/buscar/', erp_views.BoletosBusquedaView.as_view(), name='boletos_busqueda'),
    path('dashboard/erp/boletos/reportes/', erp_views.BoletosReportesView.as_view(), name='boletos_reportes'),
    path('dashboard/erp/boletos/anulaciones/', erp_views.BoletosAnulacionesView.as_view(), name='boletos_anulaciones'),
    path('dashboard/erp/boletos/importar/', erp_views.BoletosImportarView.as_view(), name='boletos_importar'),
    path('dashboard/erp/boletos/manual/', erp_views.BoletosManualView.as_view(), name='boletos_manual'),
    
    # Ventas Dashboard (Redirected to modular bookings app)
    path('dashboard/erp/ventas/', RedirectView.as_view(pattern_name='bookings:venta_list', permanent=True), name='ventas_dashboard'),
    path('dashboard/erp/ventas/nueva/', RedirectView.as_view(pattern_name='bookings:venta_create', permanent=True), name='venta_create'),
    path('dashboard/erp/ventas/<int:pk>/', RedirectView.as_view(pattern_name='bookings:venta_detail', permanent=True), name='venta_detalle'),
    path('dashboard/erp/ventas/<int:pk>/editar/', RedirectView.as_view(pattern_name='bookings:venta_update', permanent=True), name='editar_venta'),
    # path('dashboard/erp/ventas/<int:pk>/asignar-cliente/', ventas_views.VentaAssignClientView.as_view(), name='venta_asignar_cliente'),
    # path('dashboard/erp/ventas/<int:pk>/fees/add/', ventas_views.VentaAddFeeView.as_view(), name='venta_add_fee'),
    # path('dashboard/erp/ventas/<int:pk>/facturar/', ventas_views.VentaGenerateInvoiceView.as_view(), name='venta_facturar'),
    # path('dashboard/erp/ventas/<int:pk>/voucher/', ventas_views.VentaGenerateVoucherView.as_view(), name='venta_voucher'),

    # Proveedores
    path('dashboard/erp/proveedores/', proveedores_views.ProveedorListView.as_view(), name='proveedores_list'),
    path('dashboard/erp/proveedores/nuevo/', proveedores_views.ProveedorCreateView.as_view(), name='proveedor_create'),
    path('dashboard/erp/proveedores/<int:pk>/editar/', proveedores_views.ProveedorUpdateView.as_view(), name='proveedor_update'),

    # Clientes (Redirected to modular crm app)
    path('dashboard/erp/clientes/', RedirectView.as_view(pattern_name='crm:cliente_list', permanent=True), name='clientes_list'),
    path('dashboard/erp/clientes/nuevo/', RedirectView.as_view(pattern_name='crm:cliente_create', permanent=True), name='cliente_create'),
    path('dashboard/erp/clientes/<int:pk>/editar/', RedirectView.as_view(pattern_name='crm:cliente_update', permanent=True), name='cliente_update'),

    # Pasajeros (Redirected to modular crm app)
    path('dashboard/erp/pasajeros/', RedirectView.as_view(pattern_name='crm:pasajero_list', permanent=True), name='pasajeros_list'),
    path('dashboard/erp/pasajeros/nuevo/', RedirectView.as_view(pattern_name='crm:pasajero_create', permanent=True), name='pasajeros_create'),
    path('dashboard/erp/pasajeros/<int:pk>/editar/', RedirectView.as_view(pattern_name='crm:pasajero_update', permanent=True), name='pasajero_edit'),
    path('dashboard/erp/pasajeros/<int:pk>/eliminar/', RedirectView.as_view(pattern_name='crm:pasajero_delete', permanent=True), name='pasajero_delete'),

    # Configuración Agencia
    # Configuración Agencia
    path('agencia/configuracion/', agencia_views.AgenciaSettingsView.as_view(), name='agencia_settings'), 
    path('agencia/configuracion/motor-pdf/', agencia_views.MotorPdfView.as_view(), name='motor_pdf'), 
    path('agencia/usuarios/', agencia_views.AgenciaUsersListView.as_view(), name='agencia_usuarios'),
    path('agencia/usuarios/nuevo/', agencia_views.UsuarioAgenciaCreateView.as_view(), name='usuario_create'),
    path('agencia/usuarios/<int:pk>/cambiar-estado/', agencia_views.UsuarioAgenciaToggleStatusView.as_view(), name='usuario_toggle'),
    path('agencia/usuarios/<int:pk>/cambiar-rol/', agencia_views.UsuarioAgenciaUpdateRoleView.as_view(), name='usuario_update_role'),
    path('agencia/auditoria/', audit_views_frontend.AgenciaAuditLogListView.as_view(), name='agencia_auditoria'),
    
    # Configuración / Perfil
    path('setup/perfil/', user_profile_views.UserProfileView.as_view(), name='user_profile'),
    path('settings/branding/', BrandingSettingsView.as_view(), name='settings_branding'),
    

    # API endpoints
    path('api/ocr/passport/', OCRPassportView.as_view(), name='ocr_passport'),
    path('api/ocr/scan-id/', OCRPassportView.as_view(), name='api_scan_id'),
    
    path(r'api/auth/jwt/logout/', TokenLogoutView.as_view(), name='jwt_logout'),
    path(r'api/dashboard/stats/', dashboard_stats_api, name='dashboard_stats') if dashboard_stats_api else path(r'api/dashboard/stats/', lambda r: JsonResponse({'error': 'Not available'}, status=404)),
    path(r'csp-report/', csp_report_view, name='csp_report'),
    path(r'api/', include(router.urls)),
    path(r'core/api/', include((router.urls, 'core'), namespace='core-api-alias')),
    
    # Translator APIs
    path(r'api/translator/', include('core.translator_urls', namespace='translator')),
    path('tools/traductor/', __import__('core.views.translator_views', fromlist=['TraductorView']).TraductorView.as_view(), name='traductor_tool'),
    path(r'api/boletos/actualizar-item/', lambda r: __import__('core.views.dashboard_boletos', fromlist=['actualizar_item_boleto']).actualizar_item_boleto(r), name='actualizar_item_boleto'),
    
    # Dashboard y Vouchers
    path(r'api/dashboard/metricas/', lambda r: __import__('core.views.dashboard_views', fromlist=['dashboard_metricas']).dashboard_metricas(r), name='dashboard_metricas'),
    path(r'dashboard/modern/', lambda r: __import__('core.views.dashboard_views', fromlist=['DashboardView']).DashboardView.as_view()(r), name='modern_dashboard'),
    path(r'api/dashboard/alertas/', lambda r: __import__('core.views.dashboard_views', fromlist=['dashboard_alertas']).dashboard_alertas(r), name='dashboard_alertas'),
    path(r'api/ventas/<int:venta_id>/generar-voucher/', lambda r, venta_id: __import__('core.views.voucher_views', fromlist=['generar_voucher']).generar_voucher(r, venta_id), name='generar_voucher'),
    
    # Auditoría
    path(r'api/auditoria/venta/<int:venta_id>/', lambda r, venta_id: __import__('core.views.auditoria_views', fromlist=['historial_venta']).historial_venta(r, venta_id), name='historial_venta'),
    path(r'api/auditoria/estadisticas/', lambda r: __import__('core.views.auditoria_views', fromlist=['estadisticas_auditoria']).estadisticas_auditoria(r), name='estadisticas_auditoria'),
    
    # Boletos
    path(r'api/boletos/sin-venta/', lambda r: __import__('core.views.boleto_api_views', fromlist=['boletos_sin_venta']).boletos_sin_venta(r), name='boletos_sin_venta'),
    path(r'api/boletos/<int:boleto_id>/reintentar-parseo/', lambda r, boleto_id: __import__('core.views.boleto_api_views', fromlist=['reintentar_parseo']).reintentar_parseo(r, boleto_id), name='reintentar_parseo'),
    path(r'api/boletos/<int:boleto_id>/crear-venta/', lambda r, boleto_id: __import__('core.views.boleto_api_views', fromlist=['crear_venta_desde_boleto']).crear_venta_desde_boleto(r, boleto_id), name='crear_venta_desde_boleto'),
    path(r'api/boletos/dashboard-stats/', lambda r: __import__('core.views.boleto_api_views', fromlist=['dashboard_stats']).dashboard_stats(r), name='boletos_dashboard_stats'),
    path(r'api/boletos/buscar/', lambda r: __import__('core.views.boleto_api_views', fromlist=['buscar']).buscar(r), name='boletos_buscar'),
    path(r'api/boletos/reporte-comisiones/', lambda r: __import__('core.views.boleto_api_views', fromlist=['reporte_comisiones']).reporte_comisiones(r), name='boletos_reporte_comisiones'),
    path(r'api/boletos/solicitar-anulacion/', lambda r: __import__('core.views.boleto_api_views', fromlist=['solicitar_anulacion']).solicitar_anulacion(r), name='boletos_solicitar_anulacion'),
    path(r'api/boletos/<int:boleto_id>/detalle/', lambda r, boleto_id: __import__('core.views.boleto_api_views', fromlist=['detalle_boleto']).detalle_boleto(r, boleto_id), name='boletos_detalle'),
    path(r'api/boletos/<int:boleto_id>/eliminar/', lambda r, boleto_id: __import__('core.views.boleto_api_views', fromlist=['eliminar_boleto']).eliminar_boleto(r, boleto_id), name='boletos_eliminar'),
    path(r'api/boletos/mass-action/', BoletoMassActionAPIView.as_view(), name='api_boletos_mass_action'),
    path('api/boletos/<int:pk>/retry/', BoletoRetryParseAPIView.as_view(), name='api_boleto_retry'),
    path(r'api/audit-logs/', AuditLogListView.as_view(), name='api_audit_logs'),
    path(r'api/ventas/<int:pk>/double-invoice/', VentaDoubleInvoiceAPIView.as_view(), name='api_venta_double_invoice'),
    path(r'api/boletos/audit/', BoletoAuditAPIView.as_view(), name='api_boleto_audit'),
    
    # Billing/SaaS - Páginas
    path(r'billing/success/', lambda r: __import__('core.views.billing_success_views', fromlist=['billing_success']).billing_success(r), name='billing_success'),
    path(r'billing/cancel/', lambda r: __import__('core.views.billing_success_views', fromlist=['billing_cancel']).billing_cancel(r), name='billing_cancel'),
    
    # Billing/SaaS - API Básica
    path(r'api/billing/plans/', lambda r: __import__('core.views.billing_views', fromlist=['get_plans']).get_plans(r), name='billing_plans'),
    path(r'api/billing/subscription/', lambda r: __import__('core.views.billing_views', fromlist=['get_current_subscription']).get_current_subscription(r), name='current_subscription'),
    path(r'billing/pricing/', lambda r: __import__('django.views.generic', fromlist=['TemplateView']).TemplateView.as_view(template_name='billing/pricing.html')(r), name='billing_pricing'),
    path(r'api/billing/checkout/', csrf_exempt(lambda r: __import__('core.views.billing_views', fromlist=['create_checkout_session']).create_checkout_session(r)), name='create_checkout'),
    path(r'api/billing/portal/', csrf_exempt(lambda r: __import__('core.views.billing_views', fromlist=['create_portal_session']).create_portal_session(r)), name='create_portal'),
    path(r'api/billing/webhook/', csrf_exempt(lambda r: __import__('core.views.billing_views', fromlist=['stripe_webhook']).stripe_webhook(r)), name='stripe_webhook'),
    path(r'api/billing/cancel/', lambda r: __import__('core.views.billing_views', fromlist=['cancel_subscription']).cancel_subscription(r), name='cancel_subscription'),
    
    # Billing/SaaS - Dashboard
    path(r'api/billing/invoices/', lambda r: __import__('core.views.billing_dashboard_views', fromlist=['get_invoices']).get_invoices(r), name='billing_invoices'),
    path(r'api/billing/payment-method/', lambda r: __import__('core.views.billing_dashboard_views', fromlist=['get_payment_method']).get_payment_method(r), name='billing_payment_method'),
    path(r'api/billing/usage/', lambda r: __import__('core.views.billing_dashboard_views', fromlist=['get_usage_stats']).get_usage_stats(r), name='billing_usage'),
    
    # Billing/SaaS - Cambio de Plan
    path(r'api/billing/change-plan/', csrf_exempt(lambda r: __import__('core.views.billing_plan_change_views', fromlist=['change_plan']).change_plan(r)), name='change_plan'),
    path(r'api/billing/preview-change/', lambda r: __import__('core.views.billing_plan_change_views', fromlist=['preview_plan_change']).preview_plan_change(r), name='preview_plan_change'),
    path(r'api/billing/downgrade-free/', csrf_exempt(lambda r: __import__('core.views.billing_plan_change_views', fromlist=['downgrade_to_free']).downgrade_to_free(r)), name='downgrade_free'),
    
    # Billing/SaaS - Analytics (Admin only)
    path(r'api/billing/analytics/mrr/', lambda r: __import__('core.views.billing_analytics_views', fromlist=['get_mrr']).get_mrr(r), name='analytics_mrr'),
    path(r'api/billing/analytics/churn/', lambda r: __import__('core.views.billing_analytics_views', fromlist=['get_churn_rate']).get_churn_rate(r), name='analytics_churn'),
    path(r'api/billing/analytics/usage/', lambda r: __import__('core.views.billing_analytics_views', fromlist=['get_usage_metrics']).get_usage_metrics(r), name='analytics_usage'),
    path(r'api/billing/analytics/conversion/', lambda r: __import__('core.views.billing_analytics_views', fromlist=['get_conversion_funnel']).get_conversion_funnel(r), name='analytics_conversion'),
    path(r'api/billing/analytics/growth/', lambda r: __import__('core.views.billing_analytics_views', fromlist=['get_growth_metrics']).get_growth_metrics(r), name='analytics_growth'),
    
    # Reportes Contables
    path(r'api/reportes/libro-diario/', lambda r: __import__('core.views.reportes_views', fromlist=['libro_diario']).libro_diario(r), name='libro_diario'),
    path(r'api/reportes/balance-comprobacion/', lambda r: __import__('core.views.reportes_views', fromlist=['balance_comprobacion']).balance_comprobacion(r), name='balance_comprobacion'),
    path(r'api/reportes/estado-resultados/', lambda r: __import__('core.views.reportes_views', fromlist=['estado_resultados']).estado_resultados(r), name='estado_resultados'),
    path(r'api/reportes/validar-cuadre/', lambda r: __import__('core.views.reportes_views', fromlist=['validar_cuadre']).validar_cuadre(r), name='validar_cuadre'),
    path(r'api/reportes/exportar-excel/', lambda r: __import__('core.views.reportes_views', fromlist=['exportar_excel']).exportar_excel(r), name='exportar_excel'),
    
    # Setup - Crear superusuario (temporal)
    path(r'api/setup/create-superuser/', csrf_exempt(lambda r: __import__('core.views.setup_views', fromlist=['create_superuser']).create_superuser(r)), name='create_superuser'),
    
    # Cron Jobs (tareas programadas vía HTTP)
    path(r'api/cron/sincronizar-bcv/', lambda r: __import__('core.views.cron_views', fromlist=['sincronizar_bcv_cron']).sincronizar_bcv_cron(r), name='cron_sincronizar_bcv'),
    path(r'api/cron/recordatorios-pago/', lambda r: __import__('core.views.cron_views', fromlist=['enviar_recordatorios_cron']).enviar_recordatorios_cron(r), name='cron_recordatorios'),
    path(r'api/cron/cierre-mensual/', lambda r: __import__('core.views.cron_views', fromlist=['cierre_mensual_cron']).cierre_mensual_cron(r), name='cron_cierre_mensual'),
    path(r'api/cron/cargar-catalogos/', lambda r: __import__('core.views.cron_views', fromlist=['cargar_catalogos_cron']).cargar_catalogos_cron(r), name='cron_cargar_catalogos'),
    path(r'api/cron/health/', lambda r: __import__('core.views.cron_views', fromlist=['health_check']).health_check(r), name='cron_health'),
    
    # Email Monitor - Procesar correos de boletos manualmente
    path(r'api/procesar-correos-boletos/', lambda r: __import__('core.views.email_monitor_views', fromlist=['procesar_correos_boletos']).procesar_correos_boletos(r), name='procesar_correos_boletos'),
    
    # OpenAPI/Swagger Documentation
    path(r'api/schema/', lambda r: __import__('drf_spectacular.views', fromlist=['SpectacularAPIView']).SpectacularAPIView.as_view(), name='schema'),
    path(r'api/docs/', lambda r: __import__('drf_spectacular.views', fromlist=['SpectacularSwaggerView']).SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path(r'api/redoc/', lambda r: __import__('drf_spectacular.views', fromlist=['SpectacularRedocView']).SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Facturación
    path('facturacion/', facturacion_views.FacturacionDashboardView.as_view(), name='facturacion_dashboard'),
    path('facturacion/<int:pk>/', facturacion_views.FacturaDetailView.as_view(), name='factura_detalle'),
    path('facturacion/<int:pk>/pdf/', facturacion_views.descargar_pdf_factura, name='factura_pdf'),
    path('ventas/<int:pk>/facturar/', facturacion_views.generar_factura_desde_venta, name='venta_facturar'),
    path('facturacion/<int:pk>/emitir/', facturacion_views.emitir_factura_definitiva, name='factura_emitir'),

    # Cotizaciones
    path('cotizaciones/', cotizaciones_views.CotizacionDashboardView.as_view(), name='cotizacion_dashboard'),
    path('cotizaciones/magic/', cotizaciones_views.CotizacionMagicQuoterPageView.as_view(), name='cotizacion_magic'),

    path('cotizaciones/htmx/calcular/', cotizaciones_views.CotizacionHTMXCalculateTotalsView.as_view(), name='cotizacion_htmx_calcular'),
    path('cotizaciones/htmx/add-item/', cotizaciones_views.CotizacionHTMXAddItemView.as_view(), name='cotizacion_htmx_add_item'),
    path('cotizaciones/nueva/', cotizaciones_views.CotizacionCreateView.as_view(), name='cotizacion_nueva'),
    path('cotizaciones/<int:pk>/', cotizaciones_views.CotizacionDetailView.as_view(), name='cotizacion_detalle'),
    path('cotizaciones/<int:pk>/editar/', cotizaciones_views.CotizacionUpdateView.as_view(), name='cotizacion_editar'),
    path('cotizaciones/<int:pk>/cambiar-estado/', cotizaciones_views.CotizacionStatusView.as_view(), name='cotizacion_cambiar_estado'),
    path('cotizaciones/<int:pk>/pdf/', cotizaciones_views.CotizacionPDFView.as_view(), name='cotizacion_pdf'),
    path('cotizaciones/<int:pk>/convertir/', cotizaciones_views.CotizacionConvertirView.as_view(), name='cotizacion_convertir'),
    path('api/cotizaciones/magic-gpt/', cotizaciones_views.CotizacionMagicGPTView.as_view(), name='cotizacion_magic_gpt'),

    # Hotel Engine (Killer Feature)
    path('debug-check/', debug_check, name='debug_check'),
    path('hoteles/', HotelListView.as_view(), name='hotel_search'),
    path('hoteles/<slug:slug>/', HotelDetailView.as_view(), name='hotel_detail'),
    path('hoteles/<slug:slug>/story/', download_story_view, name='hotel_story'),
    path('api/marketing/generate-copy/', GenerateCopyAPI.as_view(), name='generate_copy_api'),
    path('api/marketing/generate-image/', GenerateAIImageView.as_view(), name='generate_ai_image'),
    path('marketing/hub/', MarketingHubView.as_view(), name='marketing_hub'),
    path('api/hotels/quote/', HotelQuoteAPI.as_view(), name='hotel_quote_api'),

    # Portal del Pasajero ("White-Label")
    path('v/<uuid:token>/', lambda r, token: __import__('core.views.public_views', fromlist=['PublicItineraryView']).PublicItineraryView.as_view()(r, token=token), name='public_itinerary'),
    path('v/<uuid:token>/pdf/', lambda r, token: __import__('core.views.public_views', fromlist=['PublicVoucherPDFView']).PublicVoucherPDFView.as_view()(r, token=token), name='public_voucher_pdf'),

    # Contextual Wiki & GDS Wiki
    path('api/wiki/search/', lambda r: __import__('core.views.wiki_views', fromlist=['search_wiki_context']).search_wiki_context(r), name='wiki_search'),
    path('wiki/gds/', lambda r, *a, **k: __import__('core.views.wiki_views', fromlist=['wiki_gds_list']).wiki_gds_list(r, *a, **k), name='wiki_list'),
    path('wiki/gds/<str:category>/', lambda r, category, **k: __import__('core.views.wiki_views', fromlist=['wiki_gds_reader']).wiki_gds_reader(r, category=category, **k), name='wiki_reader'),
    path('wiki/gds/<str:category>/<str:filename>/', lambda r, category, filename, **k: __import__('core.views.wiki_views', fromlist=['wiki_gds_reader']).wiki_gds_reader(r, category=category, filename=filename, **k), name='wiki_reader_file'),
    
    # Reportes / BI Dashboard (New Analytics Module)
    path('reportes/', lambda r: __import__('core.views.analytics.dashboard_views', fromlist=['AnalyticsDashboardView']).AnalyticsDashboardView.as_view()(r), name='reportes_ventas'),
    path('api/analytics/sales/', lambda r: __import__('core.views.analytics.sales_analytics', fromlist=['sales_analytics_view']).sales_analytics_view(r), name='analytics_sales'),
    path('api/analytics/finance/', lambda r: __import__('core.views.analytics.finance_analytics', fromlist=['finance_analytics_view']).finance_analytics_view(r), name='analytics_finance'),
    path('api/analytics/ops/', lambda r: __import__('core.views.analytics.ops_analytics', fromlist=['ops_analytics_view']).ops_analytics_view(r), name='analytics_ops'),
    path('reportes/exportar/', lambda r: __import__('core.views.report_export_views', fromlist=['ExportReportView']).ExportReportView.as_view()(r), name='report_export'),
    path('cotizador/', flights_views.FlightSearchView.as_view(), name='flight_search'),
    
    # Migration Requirements Checker API
    path('api/migration/check/', lambda r: __import__('core.views.migration_api', fromlist=['check_migration_requirements']).check_migration_requirements(r), name='migration_check'),
    path('api/migration/quick-check/', lambda r: __import__('core.views.migration_api', fromlist=['quick_check_visa']).quick_check_visa(r), name='migration_quick_check'),
    path('api/migration/checks/<int:pasajero_id>/', lambda r, pasajero_id: __import__('core.views.migration_api', fromlist=['get_migration_checks']).get_migration_checks(r, pasajero_id), name='migration_checks_history'),

    # Intelligence - GDS Analyzer
    path('intelligence/gds-analyzer/', GDSAnalyzerView.as_view(), name='gds_analyzer'),
    path('intelligence/gds-analyzer/ajax/', GDSAnalysisAjaxView.as_view(), name='gds_analyzer_ajax'),
    path('intelligence/gds-analyzer/inject/', GDSInjectERPView.as_view(), name='gds_analyzer_inject'),

    # --- DASHBOARD DIRECTIVO (CEO) ---
    path('ceo-dashboard/', lambda r: __import__('core.views.dashboard', fromlist=['CEODashboardView']).CEODashboardView.as_view()(r), name='ceo_dashboard'),
    path('api/ai-advisor/', lambda r: __import__('core.views.dashboard', fromlist=['AIBusinessAdvisorView']).AIBusinessAdvisorView.as_view()(r), name='ai_business_advisor'),

    # --- GOD MODE (SuperAdmin) ---
    path('god-mode/', lambda r: __import__('core.views.god_mode_views', fromlist=['GodModeDashboardView']).GodModeDashboardView.as_view()(r), name='god_mode'),
    path('god-mode/impersonate/<int:agencia_id>/', lambda r, agencia_id: __import__('core.views.god_mode_views', fromlist=['ImpersonateAgencyView']).ImpersonateAgencyView.as_view()(r, agencia_id), name='god_mode_impersonate'),
    path('god-mode/stop-impersonate/', lambda r: __import__('core.views.god_mode_views', fromlist=['StopImpersonateView']).StopImpersonateView.as_view()(r), name='god_mode_stop_impersonate'),

    # --- OMNISEARCH GLOBAL (Ctrl+K) ---
    path('omnisearch/', lambda r: __import__('core.views.search_views', fromlist=['GlobalOmnisearchView']).GlobalOmnisearchView.as_view()(r), name='omnisearch'),
    path('api/search/clientes/', lambda r: __import__('core.views.search_views', fromlist=['ClienteSearchAPIView']).ClienteSearchAPIView.as_view()(r), name='api_search_clientes'),
    path('api/crm/cedula-scanner/', CedulaScannerAPIView.as_view(), name='api_cedula_scanner'),
    
    # --- WEBHOOKS (The Invisible Agent) ---
    path('api/webhooks/resend/inbound/', lambda r: __import__('core.views.webhooks_views', fromlist=['ResendInboundWebhookView']).ResendInboundWebhookView.as_view()(r), name='webhook_resend_inbound'),
    
    # --- NOTIFICACIONES MAGIC TOAST (HTMX POLLING) ---
    path('notifications/live/', notificaciones_live_view, name='notificaciones_live'),
]

# Contenido del archivo core/urls.py
from django.shortcuts import redirect

from django.urls import reverse
def debug_check(request):
    from django.urls import get_resolver
    resolver = get_resolver()
    output = []
    output.append(f"DEBUG URL CHECK")
    output.append(f"Current namespace: {request.resolver_match.namespace if request.resolver_match else 'None'}")
    
    try:
        url = reverse('core:boletos_reportes_exportar')
        output.append(f"SUCCESS: 'core:boletos_reportes_exportar' -> {url}")
    except Exception as e:
        output.append(f"FAIL: 'core:boletos_reportes_exportar' -> {e}")

    output.append("\nALL URL NAMES:")
    for url_pattern in resolver.url_patterns:
        if hasattr(url_pattern, 'name') and url_pattern.name:
            output.append(f"Global: {url_pattern.name}")
        if hasattr(url_pattern, 'url_patterns'):
            ns = getattr(url_pattern, 'namespace', 'NoNS')
            app = getattr(url_pattern, 'app_name', 'NoApp')
            for sub in url_pattern.url_patterns:
                if hasattr(sub, 'name') and sub.name:
                    output.append(f"[{ns}/{app}]: {sub.name}")
    
    return HttpResponse("<pre>" + "\n".join(output) + "</pre>")

import json
import logging

from django.http import HttpResponse, JsonResponse
from django.urls import include, path, re_path

app_name = 'core'
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
    erp_views, proveedores_views, agencia_views,
    passport_views, home_view, pasajeros_views, user_profile_views, flights_views, audit_views_frontend,
    inventario_views
)
from apps.crm.views.clientes_views import ClienteListView, ClienteCreateView, ClienteUpdateView
from apps.marketing.views.marketing_views import GenerateAIImageView, MarketingHubView
from apps.bookings.views.ventas_views import (
    VentaDetailView, VentaCreateView, VentaUpdateView,
    VentasDashboardView, VentaAssignClientView, VentaAddFeeView,
    VentaGenerateInvoiceView, eliminar_venta
)
from apps.finance.views.facturacion_views import (
    FacturacionDashboardView, FacturaDetailView, descargar_pdf_factura,
    generar_factura_desde_venta, emitir_factura_definitiva
)
from apps.common.views.catalogos_views import (
    CatalogosCenterView, AerolineaListView, ProductoServicioListView,
    GeografiaListView, PaisListView, TipoCambioListView, TipoCambioCreateView,
    SincronizarTasasActionView, ProveedorListView, ProveedorCreateView,
    ProveedorUpdateView, ProveedorDeleteView, ComisionProveedorServicioListView,
    ComisionProveedorServicioCreateView, ComisionProveedorServicioUpdateView,
    ComisionProveedorServicioDeleteView
)
from .dashboard_stats import get_dashboard_stats as dashboard_stats_api
from .api.hotel_api import HotelQuoteAPI
from core.views.hotel_views import HotelListView, HotelDetailView, download_story_view, GenerateCopyAPI
from apps.marketing.views.marketing_views import GenerateAIImageView, MarketingHubView
from apps.crm.api import ClienteViewSet, PasajeroViewSet

# Alias para compatibilidad (Importando directamente del legacy para evitar ciclos)
from apps.bookings.views.boleto_views import (
    BoletoUploadAPIView,
    BoletoMassActionAPIView,
    VentaDoubleInvoiceAPIView,
    BoletoRetryParseAPIView,
    BoletoAuditAPIView,
    BoletoDeleteAPIView
)
from core.views.intelligence_views import GDSAnalyzerView, GDSAnalysisAjaxView, GDSInjectERPView
from core.views.audit_views import AuditLogListView

from core.views.ocr_views import OCRPassportView
from core.views.id_scanner_views import CedulaScannerAPIView
from core.views.settings_views import BrandingSettingsView
from core.views.onboarding_views import SaaSOnboardingView, OnboardingAgencyView
from core.views.notifications import notificaciones_live_view

# --- EXPLICIT VIEW IMPORTS (replacing lambdas) ---
from core.views.billing_success_views import billing_success, billing_cancel
from core.views.upload import UploadBoletoView, ReviewBoletoView, DesasociarVentaView
from core.views.upload import eliminar_boleto as eliminar_boleto_upload
from apps.bookings.views.dashboard_boletos import actualizar_item_boleto
from apps.bookings.views.dashboard_views import dashboard_metricas, DashboardView, dashboard_alertas
from core.views.voucher_views import generar_voucher
from core.views.auditoria_views import historial_venta, estadisticas_auditoria
from core.views.boleto_api_views import (
    boletos_sin_venta, reintentar_parseo, crear_venta_desde_boleto,
    dashboard_stats as boletos_dashboard_stats, buscar, reporte_comisiones,
    solicitar_anulacion, detalle_boleto, eliminar_boleto as eliminar_boleto_api,
)
from core.views.reconciliation_views import SupplierReconciliationAPIView, SupplierReconciliationUIView
from core.views.billing_views import (
    get_plans, get_current_subscription, create_checkout_session,
    create_portal_session, stripe_webhook, cancel_subscription,
)
from django.views.generic import TemplateView
from core.views.billing_dashboard_views import get_invoices, get_payment_method, get_usage_stats
from core.views.billing_plan_change_views import change_plan, preview_plan_change, downgrade_to_free
from core.views.billing_analytics_views import (
    get_mrr, get_churn_rate, get_usage_metrics, get_conversion_funnel, get_growth_metrics,
)
from core.views.reportes_views import (
    libro_diario, balance_comprobacion, estado_resultados, validar_cuadre, exportar_excel,
)
from core.views.cron_views import (
    sincronizar_bcv_cron, enviar_recordatorios_cron, cierre_mensual_cron,
    cargar_catalogos_cron, health_check,
)
from core.views.email_monitor_views import procesar_correos_boletos
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from core.views.public_views import PublicItineraryView, PublicVoucherPDFView, PublicHotelVoucherPDFView
from core.views.wiki_views import wiki_gds_list, wiki_gds_reader
from core.views.analytics.dashboard_views import AnalyticsDashboardView
from core.views.analytics.sales_analytics import sales_analytics_view
from core.views.analytics.finance_analytics import finance_analytics_view
from core.views.analytics.ops_analytics import ops_analytics_view
from core.views.report_export_views import ExportReportView
from core.views.migration_api import check_migration_requirements, quick_check_visa, get_migration_checks
from core.views.dashboard import CEODashboardView, AIBusinessAdvisorView
from core.views.god_mode_views import GodModeDashboardView, ImpersonateAgencyView, StopImpersonateView
from core.views.search_views import GlobalOmnisearchView, ClienteSearchAPIView
from core.views.webhooks_views import ResendInboundWebhookView
from core.views.translator_views import TraductorView
# --- END EXPLICIT VIEW IMPORTS ---


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
        logger = logging.getLogger('csp')
        logger.warning('CSP violation report: %s', data)
    except Exception as e:
        return JsonResponse({'detail': str(e)}, status=400)
    return JsonResponse({'detail': 'received'}, status=202)

router = DefaultRouter()

# Registro manual de APIs básicas
from rest_framework import viewsets, permissions, filters
from .serializers import PaisSerializer, CiudadSerializer, MonedaSerializer, TipoCambioSerializer, ProductoServicioSerializer, AerolineaSerializer
from apps.common.models import Pais, Ciudad, Aerolinea
from apps.finance.models.currencies import Moneda, TipoCambio
from apps.bookings.models import ProductoServicio
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

from core.api.mixins.tenant import TenantViewSetMixin

class ProductoServicioViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = ProductoServicio.objects.filter(activo=True)
    serializer_class = ProductoServicioSerializer
    permission_classes = [permissions.IsAuthenticated]
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
    # Módulos Extraídos
    path('', include('apps.bookings.urls_core')),
    path('', include('apps.common.urls_core')),
    
    # SaaS Onboarding (Público)
    path('onboarding/', SaaSOnboardingView.as_view(), name='onboarding_start'),
    path('onboarding/agency/', OnboardingAgencyView.as_view(), name='onboarding_agency'),

    # Telegram Mini Apps
    path('telegram/flyer-app/', flyer_mini_app_view, name='telegram_flyer_app'),
    path('api/generate-flyer/', generate_flyer_api, name='api_generate_flyer'),

    # Catálogos, Setup y Proveedores extraídos a apps.common.urls_core
    
    # Stripe Billing Success/Cancel
    path('billing/success/', billing_success, name='billing_success'),
    path('billing/cancel/', billing_cancel, name='billing_cancel'),
    
    # Flight Search
    path('flights/', FlightSearchView.as_view(), name='flight_search'),
    # Redirects
    path('', RedirectView.as_view(pattern_name='core:modern_dashboard', permanent=False), name='home'),
    path('dashboard/', RedirectView.as_view(pattern_name='core:modern_dashboard', permanent=False), name='dashboard_root'),

    # 🚀 REAL TIME AUTOMATION (Magic Toasts)
    
    # Rutas de Boletos movidas a apps.bookings.urls_core
    # path('api/chatbot/converse/', views.ChatbotConverseView.as_view(), name='chatbot_converse'),
    # path('api/health/', views.HealthCheckView.as_view(), name='health'),
    # path('api/auth/login/', views.LoginView.as_view(), name='login'),
    path(r'api/auth/jwt/obtain/', TokenObtainPairView.as_view(), name='jwt_obtain_pair'),
    # Dashboard ERP Boletos (Movido a urls_core)
    
    # Ventas Dashboard (Redirected to modular bookings app)
    path('dashboard/erp/ventas/', RedirectView.as_view(pattern_name='bookings:venta_list', permanent=True), name='ventas_dashboard'),
    path('dashboard/erp/ventas/nueva/', RedirectView.as_view(pattern_name='bookings:venta_create', permanent=True), name='venta_create'),
    path('dashboard/erp/ventas/<int:pk>/', RedirectView.as_view(pattern_name='bookings:venta_detail', permanent=True), name='venta_detalle'),
    path('dashboard/erp/ventas/<int:pk>/editar/', RedirectView.as_view(pattern_name='bookings:venta_update', permanent=True), name='editar_venta'),
    # path('dashboard/erp/ventas/<int:pk>/asignar-cliente/', ventas_views.VentaAssignClientView.as_view(), name='venta_asignar_cliente'),
    path('dashboard/erp/ventas/<int:pk>/fees/add/', VentaAddFeeView.as_view(), name='venta_add_fee'),
    # path('dashboard/erp/ventas/<int:pk>/facturar/', ventas_views.VentaGenerateInvoiceView.as_view(), name='venta_facturar'),
    # path('dashboard/erp/ventas/<int:pk>/voucher/', ventas_views.VentaGenerateVoucherView.as_view(), name='venta_voucher'),

    # Proveedores Dashboard ERP (Extraído a urls_core)

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
    path('tools/traductor/', TraductorView.as_view(), name='traductor_tool'),
    # API Boletos movida a urls_core
    
    # Conciliación de Proveedores
    # Movido a apps.finance.urls_core

    # Billing/SaaS - API Básica
    path(r'api/billing/plans/', get_plans, name='billing_plans'),
    path(r'api/billing/subscription/', get_current_subscription, name='current_subscription'),
    path(r'billing/pricing/', TemplateView.as_view(template_name='billing/pricing.html'), name='billing_pricing'),
    path(r'api/billing/checkout/', csrf_exempt(create_checkout_session), name='create_checkout'),
    path(r'api/billing/portal/', csrf_exempt(create_portal_session), name='create_portal'),
    path(r'api/billing/webhook/', csrf_exempt(stripe_webhook), name='stripe_webhook'),
    path(r'api/billing/cancel/', cancel_subscription, name='cancel_subscription'),
    
    # Billing/SaaS - Dashboard
    path(r'api/billing/invoices/', get_invoices, name='billing_invoices'),
    path(r'api/billing/payment-method/', get_payment_method, name='billing_payment_method'),
    path(r'api/billing/usage/', get_usage_stats, name='billing_usage'),
    
    # Billing/SaaS - Cambio de Plan
    path(r'api/billing/change-plan/', csrf_exempt(change_plan), name='change_plan'),
    path(r'api/billing/preview-change/', preview_plan_change, name='preview_plan_change'),
    path(r'api/billing/downgrade-free/', csrf_exempt(downgrade_to_free), name='downgrade_free'),
    
    # Billing/SaaS - Analytics (Admin only)
    path(r'api/billing/analytics/mrr/', get_mrr, name='analytics_mrr'),
    path(r'api/billing/analytics/churn/', get_churn_rate, name='analytics_churn'),
    path(r'api/billing/analytics/usage/', get_usage_metrics, name='analytics_usage'),
    path(r'api/billing/analytics/conversion/', get_conversion_funnel, name='analytics_conversion'),
    path(r'api/billing/analytics/growth/', get_growth_metrics, name='analytics_growth'),
    
    # Reportes Contables
    path(r'api/reportes/libro-diario/', libro_diario, name='libro_diario'),
    path(r'api/reportes/balance-comprobacion/', balance_comprobacion, name='balance_comprobacion'),
    path(r'api/reportes/estado-resultados/', estado_resultados, name='estado_resultados'),
    path(r'api/reportes/validar-cuadre/', validar_cuadre, name='validar_cuadre'),
    path(r'api/reportes/exportar-excel/', exportar_excel, name='exportar_excel'),
    

    # Cron Jobs (tareas programadas vía HTTP)
    path(r'api/cron/sincronizar-bcv/', sincronizar_bcv_cron, name='cron_sincronizar_bcv'),
    path(r'api/cron/recordatorios-pago/', enviar_recordatorios_cron, name='cron_recordatorios'),
    path(r'api/cron/cierre-mensual/', cierre_mensual_cron, name='cron_cierre_mensual'),
    path(r'api/cron/cargar-catalogos/', cargar_catalogos_cron, name='cron_cargar_catalogos'),
    path(r'api/cron/health/', health_check, name='cron_health'),
    
    # Email Monitor - Procesar correos de boletos manualmente
    path(r'api/procesar-correos-boletos/', procesar_correos_boletos, name='procesar_correos_boletos'),
    
    # OpenAPI/Swagger Documentation
    path(r'api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(r'api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path(r'api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Facturación y Finanzas
    path('', include('apps.finance.urls_core')),

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
    path('v/<uuid:token>/', PublicItineraryView.as_view(), name='public_itinerary'),
    path('v/<uuid:token>/pdf/', PublicVoucherPDFView.as_view(), name='public_voucher_pdf'),
    path('v/hotel/<int:alojamiento_id>/pdf/', PublicHotelVoucherPDFView.as_view(), name='public_hotel_voucher'),

    # Contextual Wiki & GDS Wiki
    path('api/wiki/search/', wiki_gds_list, name='wiki_search'),
    path('wiki/gds/', wiki_gds_list, name='wiki_list'),
    path('wiki/gds/<str:category>/', wiki_gds_reader, name='wiki_reader'),
    path('wiki/gds/<str:category>/<str:filename>/', wiki_gds_reader, name='wiki_reader_file'),
    
    # Reportes / BI Dashboard (New Analytics Module)
    path('reportes/', AnalyticsDashboardView.as_view(), name='reportes_ventas'),
    path('api/analytics/sales/', sales_analytics_view, name='analytics_sales'),
    path('api/analytics/finance/', finance_analytics_view, name='analytics_finance'),
    path('api/analytics/ops/', ops_analytics_view, name='analytics_ops'),
    path('reportes/exportar/', ExportReportView.as_view(), name='report_export'),
    path('cotizador/', flights_views.FlightSearchView.as_view(), name='flight_search'),
    
    # Migration Requirements Checker API
    path('api/migration/check/', check_migration_requirements, name='migration_check'),
    path('api/migration/quick-check/', quick_check_visa, name='migration_quick_check'),
    path('api/migration/checks/<int:pasajero_id>/', get_migration_checks, name='migration_checks_history'),

    # Intelligence - GDS Analyzer
    path('intelligence/gds-analyzer/', GDSAnalyzerView.as_view(), name='gds_analyzer'),
    path('intelligence/gds-analyzer/ajax/', GDSAnalysisAjaxView.as_view(), name='gds_analyzer_ajax'),
    path('intelligence/gds-analyzer/inject/', GDSInjectERPView.as_view(), name='gds_analyzer_inject'),

    # --- DASHBOARD DIRECTIVO (CEO) ---
    path('ceo-dashboard/', CEODashboardView.as_view(), name='ceo_dashboard'),
    path('api/ai-advisor/', AIBusinessAdvisorView.as_view(), name='ai_business_advisor'),

    # --- GOD MODE (SuperAdmin) ---
    path('god-mode/', GodModeDashboardView.as_view(), name='god_mode'),
    path('god-mode/impersonate/<int:agencia_id>/', ImpersonateAgencyView.as_view(), name='god_mode_impersonate'),
    path('god-mode/stop-impersonate/', StopImpersonateView.as_view(), name='god_mode_stop_impersonate'),

    # --- OMNISEARCH GLOBAL (Ctrl+K) ---
    path('omnisearch/', GlobalOmnisearchView.as_view(), name='omnisearch'),
    path('api/search/clientes/', ClienteSearchAPIView.as_view(), name='api_search_clientes'),
    path('api/crm/cedula-scanner/', CedulaScannerAPIView.as_view(), name='api_cedula_scanner'),
    
    # --- WEBHOOKS (The Invisible Agent) ---
    path('api/webhooks/resend/inbound/', ResendInboundWebhookView.as_view(), name='webhook_resend_inbound'),
    
    # --- NOTIFICACIONES MAGIC TOAST (HTMX POLLING) ---
    path('notifications/live/', notificaciones_live_view, name='notificaciones_live'),

    # --- CUENTA ---
    path('accounts/profile/', lambda r: redirect('/dashboard/'), name='account_profile'),
]

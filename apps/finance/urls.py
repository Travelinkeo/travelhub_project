from django.urls import include, path, reverse
from django.http import HttpResponse, JsonResponse
from rest_framework.routers import DefaultRouter
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt

from . import views
from .views import (
    ai_views,
    api_reconciliacion_views,
    audit_ui,
    checkout_views,
    liquidaciones_views,
    payment_views,
    reconciliacion_views,
    reconciliation_ui,
    report_ui,
    report_upload_view,
    stripe_views,
    task_status_view,
    tax_refund_views,
    views_reconciliation,
    invoice_views,
)
from core.views.billing_analytics_views import (
    get_churn_rate,
    get_conversion_funnel,
    get_growth_metrics,
    get_mrr,
    get_usage_metrics,
)
from core.views.billing_dashboard_views import get_invoices, get_payment_method, get_usage_stats
from core.views.billing_plan_change_views import change_plan, downgrade_to_free, preview_plan_change
from core.views.billing_success_views import billing_cancel, billing_success
from core.views.billing_views import (
    cancel_subscription,
    create_checkout_session,
    create_portal_session,
    get_current_subscription,
    get_plans,
    stripe_webhook,
)
from core.views.reportes_views import (
    balance_comprobacion,
    estado_resultados,
    exportar_excel,
    libro_diario,
    validar_cuadre,
)

# API ViewSets (Movidos de core/urls.py)
from rest_framework import permissions, viewsets, filters
from apps.common.models import Aerolinea, Ciudad, Pais
from apps.finance.models.currencies import Moneda, TipoCambio
from core.serializers import (
    AerolineaSerializer,
    CiudadSerializer,
    MonedaSerializer,
    PaisSerializer,
    TipoCambioSerializer,
)

class PaisViewSet(viewsets.ModelViewSet):
    queryset = Pais.objects.all()
    serializer_class = PaisSerializer
    permission_classes = [permissions.AllowAny]

class CiudadViewSet(viewsets.ModelViewSet):
    queryset = Ciudad.objects.all()
    serializer_class = CiudadSerializer
    permission_classes = [permissions.AllowAny]

class MonedaViewSet(viewsets.ModelViewSet):
    queryset = Moneda.objects.all()
    serializer_class = MonedaSerializer
    permission_classes = [permissions.AllowAny]

class TipoCambioViewSet(viewsets.ModelViewSet):
    queryset = TipoCambio.objects.all()
    serializer_class = TipoCambioSerializer
    permission_classes = [permissions.AllowAny]

class AerolineaViewSet(viewsets.ModelViewSet):
    queryset = Aerolinea.objects.filter(activa=True)
    serializer_class = AerolineaSerializer
    permission_classes = [permissions.AllowAny]



router = DefaultRouter()
router.register(r'api/reconciliacion', api_reconciliacion_views.ReporteReconciliacionViewSet, basename='api-reconciliacion')
router.register(r'paises', PaisViewSet, basename='pais')
router.register(r'ciudades', CiudadViewSet, basename='ciudad')
router.register(r'monedas', MonedaViewSet, basename='moneda')
router.register(r'tipos-cambio', TipoCambioViewSet, basename='tipocambio')
router.register(r'aerolineas', AerolineaViewSet, basename='aerolinea')

# Liquidaciones, Facturas, Comisiones
try:
    from core.views.liquidacion_views import LiquidacionProveedorViewSet, ItemLiquidacionViewSet
    from core.views.factura_consolidada_views import FacturaConsolidadaViewSet, ItemFacturaConsolidadaViewSet
    from core.views.libro_ventas_views import LibroVentasViewSet
    from core.views.tarifario_views import TarifarioProveedorViewSet, HotelTarifarioViewSet
    from core.views.catalogos_api import ComisionProveedorServicioViewSet

    router.register(r'liquidaciones', LiquidacionProveedorViewSet, basename='liquidacion')
    router.register(r'items-liquidacion', ItemLiquidacionViewSet, basename='item-liquidacion')
    router.register(r'facturas-consolidadas', FacturaConsolidadaViewSet, basename='factura-consolidada')
    router.register(r'items-factura-consolidada', ItemFacturaConsolidadaViewSet, basename='item-factura-consolidada')
    router.register(r'libro-ventas', LibroVentasViewSet, basename='libro-ventas')
    router.register(r'tarifarios', TarifarioProveedorViewSet, basename='tarifario')
    router.register(r'hoteles-tarifario', HotelTarifarioViewSet, basename='hotel-tarifario')
    router.register(r'comisiones', ComisionProveedorServicioViewSet, basename='comisiones')
except Exception as e:
    print(f"Error registering finance extra ViewSets: {e}")


app_name = 'finance'

urlpatterns = [
    # Rutas Core heredadas
    path('', include('apps.finance.urls_core')),

    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<int:pk>/issue/', views.InvoiceIssueView.as_view(), name='invoice_issue'),
    path('invoices/<int:pk>/update/', views.InvoiceUpdateView.as_view(), name='invoice_update'),
    
    # Binance Pay
    path('pago/binance/crear/<int:factura_id>/', payment_views.BinanceOrderCreateView.as_view(), name='binance_crear_orden'),
    path('pago/binance/webhook/', payment_views.BinanceWebhookView.as_view(), name='binance_webhook'), # Legacy
    
    # Red de Webhooks Blindados (Idempotencia v2)
    path('webhooks/binance/', views.BinanceWebhookView.as_view(), name='webhook_binance_resilient'),
    path('webhooks/stripe/', views.StripeWebhookView.as_view(), name='webhook_stripe_resilient'),

    # Asistente AI
    path('ai-chat/', ai_views.AIAccountingDashboardView.as_view(), name='ai_accounting_chat'),
    path('ai-chat/htmx/', ai_views.AIChatHTMXView.as_view(), name='ai_chat_htmx'),
    path('ai-chat/proposals/', ai_views.AIAccountingProposalsPartialView.as_view(), name='ai_proposals_partial'),
    path('ai-chat/proposals/<uuid:pk>/<str:action>/', ai_views.AIAccountingResolveProposalHTMXView.as_view(), name='ai_proposal_resolve_htmx'),

    # Conciliación Contable Inteligente (Fase 21) Reescritura HTMX Pura
    path('reconciliacion/dashboard/', reconciliacion_views.ReconciliationDashboardHTMXView.as_view(), name='reconciliacion_dashboard_htmx'),
    path('reconciliacion/subir/', reconciliacion_views.ReporteReconciliacionCreateView.as_view(), name='reconciliacion_create'),
    path('reconciliacion/detalle/<uuid:pk>/', reconciliacion_views.ReporteReconciliacionDetailView.as_view(), name='reconciliacion_detail'),
    path('reconciliacion/procesar-ia/<uuid:pk>/', reconciliacion_views.ProcessReconciliacionHTMXView.as_view(), name='reconciliacion_process'),
    
    # NUEVO FLUJO CABINA DE PILOTAJE (HTMX + CELERY)
    path('reconciliacion/upload/', reconciliation_ui.ReconciliationUploadView.as_view(), name='reconciliacion_upload'),
    path('reconciliacion/process-upload/', reconciliation_ui.process_reconciliation_upload_htmx, name='reconciliacion_process_upload'),
    path('reconciliacion/task-status/<str:task_id>/', reconciliation_ui.reconciliation_task_status_htmx, name='reconciliacion_task_status'),
    path('reconciliacion/results/<uuid:pk>/', audit_ui.ReconciliationResultsView.as_view(), name='reconciliacion_results'),
    path('reconciliacion/audit/approve/<int:conciliacion_id>/', audit_ui.approve_adjustment_htmx, name='audit_approve_adjustment'),
    path('reconciliacion/report/pdf/<uuid:pk>/', report_ui.download_reconciliation_report_view, name='reconciliacion_report_pdf'),
    path('reconciliacion/report/email/<uuid:pk>/', report_ui.send_reconciliation_report_email_htmx, name='reconciliacion_report_email'),
    path('tax-refund/', tax_refund_views.TaxRefundDashboardView.as_view(), name='tax_refund_dashboard'),
    path('tax-refund/iniciar/<uuid:reclamo_id>/', tax_refund_views.IniciarTramiteRefundView.as_view(), name='iniciar_tax_refund'),

    # API Analytics Anterior 
    path('api/reconciliacion/stats/', api_reconciliacion_views.ReconciliationDashboardStatsAPIView.as_view(), name='api_reconciliacion_stats'),
    path('api/reconciliacion/upload-async/', views_reconciliation.ReporteReconciliacionAsyncUploadAPIView.as_view(), name='api_reconciliacion_upload_async'),
    
    # Staging Ledger Buffer (Propuestas de Transacción IA)
    path('api/finance/propuestas/', ai_views.PropuestaTransaccionIAListCreateAPIView.as_view(), name='api_propuestas_list'),
    path('api/finance/propuestas/<uuid:pk>/<str:action>/', ai_views.ResolvePropuestaAPIView.as_view(), name='api_propuesta_resolve'),

    path('', include(router.urls)),
    
    path('profitability/', views.ProfitabilityDashboardView.as_view(), name='profit_dashboard'),
    path('api/profit-series/', views.ProfitSeriesDataView.as_view(), name='profit_series_api'),

    # Liquidaciones a Proveedores
    path('liquidaciones/', liquidaciones_views.LiquidacionListView.as_view(), name='liquidacion_list'),
    path('liquidaciones/nueva/', liquidaciones_views.LiquidacionCreateView.as_view(), name='liquidacion_create'),
    path('liquidaciones/<int:pk>/', liquidaciones_views.LiquidacionDetailView.as_view(), name='liquidacion_detail'),

    # MOTOR HÍBRIDO (AUDI ENGINE v3.0)
    path('api/finance/reconciliacion/upload/', report_upload_view.ReporteProveedorUploadAPIView.as_view(), name='api_finance_reconciliacion_upload'),
    path('api/finance/task-status/<str:task_id>/', task_status_view.ReconciliationTaskStatusAPIView.as_view(), name='api_finance_task_status'),

    # MAGIC LINK CHECKOUT (B2C)
    path('pay/<uuid:uuid_link>/', checkout_views.MagicLinkCheckoutView.as_view(), name='magic_link_checkout'),
    
    # Stripe Checkout & Webhook
    path('pay/<uuid:uuid_link>/stripe/', stripe_views.StripeCheckoutView.as_view(), name='stripe_checkout'),
    path('webhook/stripe/', stripe_views.StripeWebhookView.as_view(), name='stripe_webhook'),

    # Billing/SaaS (Movido de core/urls.py)
    path('billing/success/', billing_success, name='billing_success'),
    path('billing/cancel/', billing_cancel, name='billing_cancel'),
    path('api/billing/plans/', get_plans, name='billing_plans'),
    path('api/billing/subscription/', get_current_subscription, name='current_subscription'),
    path('pricing/', TemplateView.as_view(template_name='billing/pricing.html'), name='billing_pricing'),
    path('api/billing/checkout/', csrf_exempt(create_checkout_session), name='create_checkout'),
    path('api/billing/portal/', csrf_exempt(create_portal_session), name='create_portal'),
    path('api/billing/webhook/', csrf_exempt(stripe_webhook), name='stripe_webhook_v1'), # Alias para evitar conflicto si existe
    path('api/billing/cancel/', cancel_subscription, name='cancel_subscription'),
    
    # Billing/SaaS - Dashboard
    path('api/billing/invoices/', get_invoices, name='billing_invoices'),
    path('api/billing/payment-method/', get_payment_method, name='billing_payment_method'),
    path('api/billing/usage/', get_usage_stats, name='billing_usage'),
    
    # Billing/SaaS - Cambio de Plan
    path('api/billing/change-plan/', csrf_exempt(change_plan), name='change_plan'),
    path('api/billing/preview-change/', preview_plan_change, name='preview_plan_change'),
    path('api/billing/downgrade-free/', csrf_exempt(downgrade_to_free), name='downgrade_free'),
    
    # Billing/SaaS - Analytics
    path('api/billing/analytics/mrr/', get_mrr, name='analytics_mrr'),
    path('api/billing/analytics/churn/', get_churn_rate, name='analytics_churn'),
    path('api/billing/analytics/usage/', get_usage_metrics, name='analytics_usage'),
    path('api/billing/analytics/conversion/', get_conversion_funnel, name='analytics_conversion'),
    path('api/billing/analytics/growth/', get_growth_metrics, name='analytics_growth'),
    
    # Reportes Contables
    path('api/reportes/libro-diario/', libro_diario, name='libro_diario'),
    path('api/reportes/balance-comprobacion/', balance_comprobacion, name='balance_comprobacion'),
    path('api/reportes/estado-resultados/', estado_resultados, name='estado_resultados'),
    path('api/reportes/validar-cuadre/', validar_cuadre, name='validar_cuadre'),
    path('api/reportes/exportar-excel/', exportar_excel, name='exportar_excel'),

    # Dashboard de Revisión de Facturas (Manual Review)
    path('facturas-proveedores/revisar/', invoice_views.InvoiceReviewDashboardView.as_view(), name='invoice_review_dashboard'),
    path('facturas-proveedores/vincular/<int:factura_id>/', invoice_views.force_match_invoice_htmx, name='force_match_invoice'),
]


from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import payment_views, ai_views, liquidaciones_views, api_reconciliacion_views, reconciliacion_views, views_reconciliation, report_upload_view, task_status_view, reconciliation_ui, audit_ui, report_ui, checkout_views, stripe_views, tax_refund_views

router = DefaultRouter()
router.register(r'api/reconciliacion', api_reconciliacion_views.ReporteReconciliacionViewSet, basename='api-reconciliacion')

app_name = 'finance'

urlpatterns = [
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
]

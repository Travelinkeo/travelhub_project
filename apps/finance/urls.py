from django.urls import path
from . import views
from .views import payment_views, ai_views, liquidaciones_views

app_name = 'finance'

urlpatterns = [
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<int:pk>/issue/', views.InvoiceIssueView.as_view(), name='invoice_issue'),
    path('invoices/<int:pk>/update/', views.InvoiceUpdateView.as_view(), name='invoice_update'),
    
    # Binance Pay
    path('pago/binance/crear/<int:factura_id>/', payment_views.BinanceOrderCreateView.as_view(), name='binance_crear_orden'),
    path('pago/binance/webhook/', payment_views.BinanceWebhookView.as_view(), name='binance_webhook'),

    # Asistente AI
    path('ai-chat/', ai_views.AIAccountingChatView.as_view(), name='ai_accounting_chat'),
    path('ai-chat/htmx/', ai_views.AIChatHTMXView.as_view(), name='ai_chat_htmx'),

    # Conciliación
    path('reconciliation/', views.ReportListView.as_view(), name='report_list'),
    path('reconciliation/upload/', views.ReportUploadView.as_view(), name='report_upload'),
    path('reconciliation/<int:pk>/', views.ReconciliationDetailView.as_view(), name='report_detail'),
    path('reconciliation/resolve-ai/<int:pk>/', views.ResolveDiscrepancyAIView.as_view(), name='resolve_discrepancy_ai'),
    # Rentabilidad
    path('profitability/', views.ProfitabilityDashboardView.as_view(), name='profit_dashboard'),
    path('api/profit-series/', views.ProfitSeriesDataView.as_view(), name='profit_series_api'),

    # Liquidaciones a Proveedores
    path('liquidaciones/', liquidaciones_views.LiquidacionListView.as_view(), name='liquidacion_list'),
    path('liquidaciones/nueva/', liquidaciones_views.LiquidacionCreateView.as_view(), name='liquidacion_create'),
    path('liquidaciones/<int:pk>/', liquidaciones_views.LiquidacionDetailView.as_view(), name='liquidacion_detail'),
]

import logging

from django.urls import include, path
from django.utils.module_loading import import_string
from rest_framework import permissions, viewsets
from rest_framework.routers import DefaultRouter

from apps.common.models import Aerolinea, Ciudad, Pais
from core.serializers import AerolineaSerializer, CiudadSerializer, PaisSerializer

from . import views
from .views import invoice_views, payment_views

logger = logging.getLogger(__name__)


class PaisViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaisSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Pais.objects.all()


class CiudadViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CiudadSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Ciudad.objects.all()


class AerolineaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AerolineaSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Aerolinea.objects.filter(activa=True)


router = DefaultRouter()
router.register(r"facturas", invoice_views.FacturaViewSet, basename="factura")
router.register(r"paises", PaisViewSet, basename="pais")
router.register(r"ciudades", CiudadViewSet, basename="ciudad")
router.register(r"aerolineas", AerolineaViewSet, basename="aerolinea")

try:
    FacturaConsolidadaViewSet = import_string(
        "core.views.factura_consolidada_views.FacturaConsolidadaViewSet"
    )
    ItemFacturaConsolidadaViewSet = import_string(
        "core.views.factura_consolidada_views.ItemFacturaConsolidadaViewSet"
    )
    LibroVentasViewSet = import_string("core.views.libro_ventas_views.LibroVentasViewSet")
    HotelTarifarioViewSet = import_string("core.views.tarifario_views.HotelTarifarioViewSet")
    TarifarioProveedorViewSet = import_string(
        "core.views.tarifario_views.TarifarioProveedorViewSet"
    )
    ComisionProveedorServicioViewSet = import_string(
        "core.views.catalogos_api.ComisionProveedorServicioViewSet"
    )

    router.register(
        r"facturas-consolidadas", FacturaConsolidadaViewSet, basename="factura-consolidada"
    )
    router.register(
        r"items-factura-consolidada",
        ItemFacturaConsolidadaViewSet,
        basename="item-factura-consolidada",
    )
    router.register(r"libro-ventas", LibroVentasViewSet, basename="libro-ventas")
    router.register(r"tarifarios", TarifarioProveedorViewSet, basename="tarifario")
    router.register(r"hoteles-tarifario", HotelTarifarioViewSet, basename="hotel-tarifario")
    router.register(r"comisiones", ComisionProveedorServicioViewSet, basename="comisiones")
except Exception as e:
    logger.error(f"Error registering finance extra ViewSets: {e}")


app_name = "finance"

urlpatterns = [
    path("", include("apps.finance.urls_core")),
    # Facturas
    path("invoices/", views.InvoiceListView.as_view(), name="invoice_list"),
    path("invoices/<int:pk>/", views.InvoiceDetailView.as_view(), name="invoice_detail"),
    path("invoices/<int:pk>/issue/", views.InvoiceIssueView.as_view(), name="invoice_issue"),
    path("invoices/<int:pk>/update/", views.InvoiceUpdateView.as_view(), name="invoice_update"),
    path(
        "api/ventas/<int:pk>/double-invoice/",
        invoice_views.VentaDoubleInvoiceAPIView.as_view(),
        name="api_venta_double_invoice",
    ),
    # Pagos
    path(
        "venta/<int:venta_id>/registrar-pago/",
        payment_views.registrar_pago_modal_view,
        name="registrar_pago_fast",
    ),
    # Webhooks blindados
    path("webhooks/binance/", views.BinanceWebhookView.as_view(), name="webhook_binance_resilient"),
    path("webhooks/stripe/", views.StripeWebhookView.as_view(), name="webhook_stripe_resilient"),
    path(
        "webhooks/telegram/staff-control/",
        views.TelegramBotWebhookView.as_view(),
        name="webhook_telegram_staff_control",
    ),
    # B2C Checkout (ELIMINADO: LinkDePago)
    # BI / Profitability
    path("profitability/", views.ProfitabilityDashboardView.as_view(), name="profit_dashboard"),
    path("bi/", views.BIDashboardView.as_view(), name="dashboard_bi"),
    path("audit-log/", views.AuditTimelineView.as_view(), name="audit_timeline"),
    path("api/profit-series/", views.ProfitSeriesDataView.as_view(), name="profit_series_api"),
    # Billing/SaaS
    path(
        "billing/success/",
        import_string("core.views.billing_success_views.billing_success"),
        name="billing_success",
    ),
    path(
        "billing/cancel/",
        import_string("core.views.billing_success_views.billing_cancel"),
        name="billing_cancel",
    ),
    path(
        "api/billing/plans/",
        import_string("core.views.billing_views.get_plans"),
        name="billing_plans",
    ),
    path(
        "api/billing/subscription/",
        import_string("core.views.billing_views.get_current_subscription"),
        name="current_subscription",
    ),
    path(
        "pricing/",
        import_string("django.views.generic.TemplateView").as_view(
            template_name="billing/pricing.html"
        ),
        name="billing_pricing",
    ),
    path(
        "api/billing/checkout/",
        import_string("core.views.billing_views.create_checkout_session"),
        name="create_checkout",
    ),
    path(
        "api/billing/portal/",
        import_string("core.views.billing_views.create_portal_session"),
        name="create_portal",
    ),
    path(
        "api/billing/cancel/",
        import_string("core.views.billing_views.cancel_subscription"),
        name="cancel_subscription",
    ),
    path(
        "api/billing/invoices/",
        import_string("core.views.billing_dashboard_views.get_invoices"),
        name="billing_invoices",
    ),
    path(
        "api/billing/payment-method/",
        import_string("core.views.billing_dashboard_views.get_payment_method"),
        name="billing_payment_method",
    ),
    path(
        "api/billing/usage/",
        import_string("core.views.billing_dashboard_views.get_usage_stats"),
        name="billing_usage",
    ),
    path(
        "api/billing/change-plan/",
        import_string("core.views.billing_plan_change_views.change_plan"),
        name="change_plan",
    ),
    path(
        "api/billing/preview-change/",
        import_string("core.views.billing_plan_change_views.preview_plan_change"),
        name="preview_plan_change",
    ),
    path(
        "api/billing/downgrade-free/",
        import_string("core.views.billing_plan_change_views.downgrade_to_free"),
        name="downgrade_free",
    ),
    path(
        "api/billing/analytics/mrr/",
        import_string("core.views.billing_analytics_views.get_mrr"),
        name="analytics_mrr",
    ),
    path(
        "api/billing/analytics/churn/",
        import_string("core.views.billing_analytics_views.get_churn_rate"),
        name="analytics_churn",
    ),
    path(
        "api/billing/analytics/usage/",
        import_string("core.views.billing_analytics_views.get_usage_metrics"),
        name="analytics_usage",
    ),
    path(
        "api/billing/analytics/conversion/",
        import_string("core.views.billing_analytics_views.get_conversion_funnel"),
        name="analytics_conversion",
    ),
    path(
        "api/billing/analytics/growth/",
        import_string("core.views.billing_analytics_views.get_growth_metrics"),
        name="analytics_growth",
    ),
    # Reportes Contables
    path(
        "api/reportes/libro-diario/",
        import_string("core.views.reportes_views.libro_diario"),
        name="libro_diario",
    ),
    path(
        "api/reportes/balance-comprobacion/",
        import_string("core.views.reportes_views.balance_comprobacion"),
        name="balance_comprobacion",
    ),
    path(
        "api/reportes/estado-resultados/",
        import_string("core.views.reportes_views.estado_resultados"),
        name="estado_resultados",
    ),
    path(
        "api/reportes/validar-cuadre/",
        import_string("core.views.reportes_views.validar_cuadre"),
        name="validar_cuadre",
    ),
    path(
        "api/reportes/exportar-excel/",
        import_string("core.views.reportes_views.exportar_excel"),
        name="exportar_excel",
    ),
    path("", include(router.urls)),
]

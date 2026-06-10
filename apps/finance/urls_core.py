from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from apps.finance.views.facturacion_views import (
    FacturacionDashboardView,
    FacturaDetailView,
    descargar_pdf_factura,
    emitir_factura_definitiva,
    generar_factura_desde_venta,
)


def dynamic_view(view_path):
    from django.utils.module_loading import import_string

    def lazy_view_handler(request, *args, **kwargs):
        view_class = import_string(view_path)
        return view_class.as_view()(request, *args, **kwargs)

    return lazy_view_handler


urlpatterns = [
    # Facturación
    path("facturacion/", FacturacionDashboardView.as_view(), name="facturacion_dashboard"),
    path("facturacion/<int:pk>/", FacturaDetailView.as_view(), name="factura_detalle"),
    path("facturacion/<int:pk>/pdf/", descargar_pdf_factura, name="factura_pdf"),
    path("ventas/<int:pk>/facturar/", generar_factura_desde_venta, name="venta_facturar"),
    path("facturacion/<int:pk>/emitir/", emitir_factura_definitiva, name="factura_emitir"),
    # Conciliación de Proveedores
    path(
        "api/reconciliation/",
        csrf_exempt(dynamic_view("core.views.reconciliation_views.SupplierReconciliationAPIView")),
        name="api_reconciliation",
    ),
    path(
        "finance/supplier-reconciliation/",
        dynamic_view("core.views.reconciliation_views.SupplierReconciliationUIView"),
        name="supplier_reconciliation_ui",
    ),
]

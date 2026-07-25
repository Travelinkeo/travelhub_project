"""Módulo urls core de la aplicación finance.
"""

from django.urls import path
from django.utils.module_loading import import_string
from django.views.decorators.csrf import csrf_exempt

from apps.finance.views.facturacion_views import (
    FacturacionDashboardView,
    FacturaDetailView,
    descargar_pdf_factura,
    emitir_factura_definitiva,
    generar_factura_desde_venta,
)


def dynamic_view(view_path):
    # dynamic_view: Dynamic view. Args: según implementación. Returns: según implementación.
    from django.utils.module_loading import import_string

    def lazy_view_handler(request, *args, **kwargs):
        # lazy_view_handler: Lazy view handler. Args: según implementación. Returns: según implementación.
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
    # Conciliación de Proveedores / Liquidaciones
    path(
        "supplier-reconciliation/",
        import_string("apps.contabilidad.views.reconciliation_view"),
        name="supplier_reconciliation_ui",
    ),
]

from django.urls import path
from apps.finance.views.facturacion_views import (
    FacturacionDashboardView, FacturaDetailView, descargar_pdf_factura,
    generar_factura_desde_venta, emitir_factura_definitiva
)
from core.views.reconciliation_views import SupplierReconciliationAPIView, SupplierReconciliationUIView
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    # Facturación
    path('facturacion/', FacturacionDashboardView.as_view(), name='facturacion_dashboard'),
    path('facturacion/<int:pk>/', FacturaDetailView.as_view(), name='factura_detalle'),
    path('facturacion/<int:pk>/pdf/', descargar_pdf_factura, name='factura_pdf'),
    path('ventas/<int:pk>/facturar/', generar_factura_desde_venta, name='venta_facturar'),
    path('facturacion/<int:pk>/emitir/', emitir_factura_definitiva, name='factura_emitir'),

    # Conciliación de Proveedores
    path('api/reconciliation/', csrf_exempt(SupplierReconciliationAPIView.as_view()), name='api_reconciliation'),
    path('finance/supplier-reconciliation/', SupplierReconciliationUIView.as_view(), name='supplier_reconciliation_ui'),
]

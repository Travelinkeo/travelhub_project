from django.urls import path

from apps.bookings.bookings_views import (
    FeeVentaCreateView,
    ItemVentaCreateView,
    ItemVentaUpdateView,
    PagoVentaCreateView,
    RevenueLeakDashboardView,
    VentaCreateView,
    VentaDeleteView,
    VentaDetailView,
    VentaListView,
    VentaTimelineView,
    VentaUpdateView,
    dashboard_main,
    dashboard_stats_htmx,
    resolve_finding_htmx,
    whatsapp_pairing_code_view,
    whatsapp_qr_view,
)

app_name = 'bookings'

urlpatterns = [
    # Ventas
    path('ventas/', VentaListView.as_view(), name='venta_list'),
    path('ventas/nueva/', VentaCreateView.as_view(), name='venta_create'),
    path('ventas/<int:pk>/', VentaDetailView.as_view(), name='venta_detail'),
    path('ventas/<int:pk>/timeline/', VentaTimelineView.as_view(), name='venta_timeline'),
    path('ventas/<int:pk>/editar/', VentaUpdateView.as_view(), name='venta_update'),
    path('ventas/<int:pk>/eliminar/', VentaDeleteView.as_view(), name='venta_delete'),

    # Inteligencia & Auditoría
    path('auditoria/', RevenueLeakDashboardView.as_view(), name='revenue_leak_dashboard'),
    path('auditoria/<int:pk>/resolver/', resolve_finding_htmx, name='resolve_finding'),

    # HTMX Inline actions for Venta Detail
    path('ventas/<int:venta_pk>/items/agregar/', ItemVentaCreateView.as_view(), name='item_venta_add'),
    path('ventas/items/<int:pk>/editar/', ItemVentaUpdateView.as_view(), name='item_venta_edit'),
    path('ventas/<int:venta_pk>/fees/agregar/', FeeVentaCreateView.as_view(), name='fee_venta_add'),
    path('ventas/<int:venta_pk>/pagos/agregar/', PagoVentaCreateView.as_view(), name='pago_venta_add'),
    # Dashboard de Flujo de Caja
    path('dashboard/', dashboard_main, name='dashboard_main'),
    path('dashboard/stats/', dashboard_stats_htmx, name='dashboard_stats'),
    path('dashboard/whatsapp-qr/', whatsapp_qr_view, name='whatsapp_qr'),
    path('dashboard/whatsapp-pairing/', whatsapp_pairing_code_view, name='whatsapp_pairing'),
]
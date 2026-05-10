from django.urls import path
from apps.bookings.views.boleto_views import (
    BoletoUploadAPIView,
    BoletoMassActionAPIView,
    VentaDoubleInvoiceAPIView,
    BoletoRetryParseAPIView,
    BoletoAuditAPIView,
    BoletoDeleteAPIView
)
from core.views import erp_views
from core.views.upload import UploadBoletoView, ReviewBoletoView, DesasociarVentaView
from core.views.upload import eliminar_boleto as eliminar_boleto_upload
from core.views.boleto_api_views import (
    boletos_sin_venta, reintentar_parseo, crear_venta_desde_boleto,
    dashboard_stats as boletos_dashboard_stats, buscar, reporte_comisiones,
    solicitar_anulacion, detalle_boleto, eliminar_boleto as eliminar_boleto_api,
)
from apps.bookings.views.dashboard_boletos import actualizar_item_boleto

urlpatterns = [
    # Carga de Boletos y IA
    path('api/boletos/upload/', BoletoUploadAPIView.as_view(), name='api_boleto_upload'),
    path('api/boletos/<int:pk>/delete/', BoletoDeleteAPIView.as_view(), name='api_boleto_delete'),
    path('api/boletos/mass-action/', BoletoMassActionAPIView.as_view(), name='api_boletos_mass_action'),
    path('api/boletos/<int:pk>/retry/', BoletoRetryParseAPIView.as_view(), name='api_boleto_retry'),
    path('api/boletos/audit/', BoletoAuditAPIView.as_view(), name='api_boleto_audit'),
    path('api/ventas/<int:pk>/double-invoice/', VentaDoubleInvoiceAPIView.as_view(), name='api_venta_double_invoice'),
    
    # UI Vistas Clásicas de Boletos
    path('upload/boleto/', UploadBoletoView.as_view(), name='upload_boleto'),
    path('upload/boleto/<int:pk>/revisar/', ReviewBoletoView.as_view(), name='revisar_boleto'),
    path('upload/boleto/<int:pk>/desasociar-venta/', DesasociarVentaView.as_view(), name='desasociar_venta'),
    path('upload/boleto/<int:pk>/eliminar-fisicamente/', eliminar_boleto_upload, name='eliminar_boleto_hard'),
    
    # ERP Boletos Dashboard
    path('dashboard/erp/boletos/', erp_views.DashboardBoletosView.as_view(), name='boletos_dashboard'),
    path('dashboard/erp/boletos/buscar/', erp_views.BoletosBusquedaView.as_view(), name='boletos_busqueda'),
    path('dashboard/erp/boletos/reportes/', erp_views.BoletosReportesView.as_view(), name='boletos_reportes'),
    path('dashboard/erp/boletos/reportes/exportar/', erp_views.ExportarBoletosExcelView.as_view(), name='boletos_reportes_exportar'),
    path('dashboard/erp/boletos/anulaciones/', erp_views.BoletosAnulacionesView.as_view(), name='boletos_anulaciones'),
    path('dashboard/erp/boletos/importar/', erp_views.BoletosImportarView.as_view(), name='boletos_importar'),
    path('dashboard/erp/boletos/manual/', erp_views.BoletosManualView.as_view(), name='boletos_manual'),
    
    # API Boletos
    path('api/boletos/actualizar-item/', actualizar_item_boleto, name='actualizar_item_boleto'),
    path('api/boletos/sin-venta/', boletos_sin_venta, name='boletos_sin_venta'),
    path('api/boletos/<int:boleto_id>/reintentar-parseo/', reintentar_parseo, name='reintentar_parseo'),
    path('api/boletos/<int:boleto_id>/crear-venta/', crear_venta_desde_boleto, name='crear_venta_desde_boleto'),
    path('api/boletos/dashboard-stats/', boletos_dashboard_stats, name='boletos_dashboard_stats'),
    path('api/boletos/buscar/', buscar, name='boletos_buscar'),
    path('api/boletos/reporte-comisiones/', reporte_comisiones, name='boletos_reporte_comisiones'),
    path('api/boletos/solicitar-anulacion/', solicitar_anulacion, name='boletos_solicitar_anulacion'),
    path('api/boletos/<int:boleto_id>/detalle/', detalle_boleto, name='boletos_detalle'),
    path('api/boletos/<int:boleto_id>/eliminar/', eliminar_boleto_api, name='boletos_eliminar'),
]

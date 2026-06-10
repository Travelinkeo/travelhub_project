from django.urls import path
from django.utils.module_loading import import_string

from apps.bookings.views.boleto_views import (
    BoletoAuditAPIView,
    BoletoDeleteAPIView,
    BoletoMassActionAPIView,
    BoletoRetryParseAPIView,
    BoletoUploadAPIView,
)
from apps.bookings.views.dashboard_boletos import actualizar_item_boleto


def dynamic_view(view_path):
    def lazy_view_handler(request, *args, **kwargs):
        view_class = import_string(view_path)
        return view_class.as_view()(request, *args, **kwargs)

    return lazy_view_handler


def dynamic_fb_view(view_path):
    def lazy_view_handler(request, *args, **kwargs):
        view_fn = import_string(view_path)
        return view_fn(request, *args, **kwargs)

    return lazy_view_handler


urlpatterns = [
    # Carga de Boletos y IA
    path("api/boletos/upload/", BoletoUploadAPIView.as_view(), name="api_boleto_upload"),
    path("api/boletos/<int:pk>/delete/", BoletoDeleteAPIView.as_view(), name="api_boleto_delete"),
    path(
        "api/boletos/mass-action/",
        BoletoMassActionAPIView.as_view(),
        name="api_boletos_mass_action",
    ),
    path("api/boletos/<int:pk>/retry/", BoletoRetryParseAPIView.as_view(), name="api_boleto_retry"),
    path("api/boletos/audit/", BoletoAuditAPIView.as_view(), name="api_boleto_audit"),
    # UI Vistas Clásicas de Boletos
    path(
        "upload/boleto/", dynamic_view("core.views.upload.UploadBoletoView"), name="upload_boleto"
    ),
    path(
        "upload/boleto/<int:pk>/revisar/",
        dynamic_view("core.views.upload.ReviewBoletoView"),
        name="revisar_boleto",
    ),
    path(
        "upload/boleto/<int:pk>/desasociar-venta/",
        dynamic_view("core.views.upload.DesasociarVentaView"),
        name="desasociar_venta",
    ),
    path(
        "upload/boleto/<int:pk>/eliminar-fisicamente/",
        dynamic_fb_view("core.views.upload.eliminar_boleto"),
        name="eliminar_boleto_hard",
    ),
    # Ventas
    # ERP Boletos Dashboard
    path(
        "dashboard/erp/boletos/",
        dynamic_view("core.views.erp_views.DashboardBoletosView"),
        name="boletos_dashboard",
    ),
    path(
        "dashboard/erp/boletos/buscar/",
        dynamic_view("core.views.erp_views.BoletosBusquedaView"),
        name="boletos_busqueda",
    ),
    path(
        "dashboard/erp/boletos/reportes/",
        dynamic_view("core.views.erp_views.BoletosReportesView"),
        name="boletos_reportes",
    ),
    path(
        "dashboard/erp/boletos/reportes/exportar/",
        dynamic_view("core.views.erp_views.ExportarBoletosExcelView"),
        name="boletos_reportes_exportar",
    ),
    path(
        "dashboard/erp/boletos/anulaciones/",
        dynamic_view("core.views.erp_views.BoletosAnulacionesView"),
        name="boletos_anulaciones",
    ),
    path(
        "dashboard/erp/boletos/importar/",
        dynamic_view("core.views.erp_views.BoletosImportarView"),
        name="boletos_importar",
    ),
    path(
        "dashboard/erp/boletos/manual/",
        dynamic_view("core.views.erp_views.BoletosManualView"),
        name="boletos_manual",
    ),
    # API Boletos
    path("api/boletos/actualizar-item/", actualizar_item_boleto, name="actualizar_item_boleto"),
    path(
        "api/boletos/sin-venta/",
        dynamic_fb_view("core.views.boleto_api_views.boletos_sin_venta"),
        name="boletos_sin_venta",
    ),
    path(
        "api/boletos/<int:boleto_id>/reintentar-parseo/",
        dynamic_fb_view("core.views.boleto_api_views.reintentar_parseo"),
        name="reintentar_parseo",
    ),
    path(
        "api/boletos/<int:boleto_id>/crear-venta/",
        dynamic_fb_view("core.views.boleto_api_views.crear_venta_desde_boleto"),
        name="crear_venta_desde_boleto",
    ),
    path(
        "api/boletos/dashboard-stats/",
        dynamic_fb_view("core.views.boleto_api_views.dashboard_stats"),
        name="boletos_dashboard_stats",
    ),
    path(
        "api/boletos/buscar/",
        dynamic_fb_view("core.views.boleto_api_views.buscar"),
        name="boletos_buscar",
    ),
    path(
        "api/boletos/reporte-comisiones/",
        dynamic_fb_view("core.views.boleto_api_views.reporte_comisiones"),
        name="boletos_reporte_comisiones",
    ),
    path(
        "api/boletos/solicitar-anulacion/",
        dynamic_fb_view("core.views.boleto_api_views.solicitar_anulacion"),
        name="boletos_solicitar_anulacion",
    ),
    path(
        "api/boletos/<int:boleto_id>/detalle/",
        dynamic_fb_view("core.views.boleto_api_views.detalle_boleto"),
        name="boletos_detalle",
    ),
    path(
        "api/boletos/<int:boleto_id>/eliminar/",
        dynamic_fb_view("core.views.boleto_api_views.eliminar_boleto"),
        name="boletos_eliminar",
    ),
]

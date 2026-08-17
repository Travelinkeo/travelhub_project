from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.bookings.bookings_views import VentaDeleteView, VentaUpdateView
from apps.bookings.views.boleto_views import (
    BoletoAuditAPIView,
    BoletoDeleteAPIView,
    BoletoUploadAPIView,
)
from apps.bookings.views.dashboard_views import DashboardView
from apps.cotizaciones.views import (
    CotizacionConvertirView,
    CotizacionCreateView,
    CotizacionDetailView,
    CotizacionPDFView,
    CotizacionStatusView,
    CotizacionUpdateView,
)
from apps.finance.views.facturacion_views import (
    FacturaDetailView,
    descargar_pdf_factura,
    emitir_factura_definitiva,
    generar_factura_desde_venta,
)
from apps.marketing.views.marketing_views import MarketingHubView
from core.api.hotel_api import HotelQuoteAPI
from core.dashboard_stats import get_dashboard_stats as dashboard_stats_api
from core.metrics import health_metrics_view
from core.middleware import csp_report_view
from core.views import reportes_views
from core.views.analytics import dashboard_views, finance_analytics, ops_analytics, sales_analytics
from core.views.billing_views import AccountBillingView
from core.views.boleto_api_views import reintentar_parseo as api_reintentar_parseo
from core.views.flights_views import FlightSearchView
from core.views.hotel_views import (
    GenerateCopyAPI,
    HotelDetailView,
    HotelListView,
    download_story_view,
)
from core.views.marketing_views import demo_page, demo_request, lead_magnet_download, parse_demo
from core.views.voucher_views import generar_voucher

from .views import (
    agencia_views,
    audit_views_frontend,
    auth_views,
    boleto_api_views,
    cron_views,
    dashboard,
    email_monitor_views,
    erp_views,
    evolution_proxy_views,
    evolution_qr_view,
    god_mode_views,
    health_views,
    intelligence_views,
    notifications,
    settings_views,
    translator_views,
    user_profile_views,
    webhooks_views,
    wiki_views,
)
from .views import upload as upload_views

app_name = "core"

urlpatterns = [
    # Demo & Marketing HTMX Endpoints
    path("demo/", demo_page, name="demo_page"),
    path("api/parse-demo/", parse_demo, name="parse_demo"),
    path("api/lead-magnet/", lead_magnet_download, name="lead_magnet_download"),
    path("api/demo-request/", demo_request, name="demo_request"),
    # Configuración Agencia
    path(
        "agencia/configuracion/",
        agencia_views.AgenciaSettingsView.as_view(),
        name="agencia_settings",
    ),
    path(
        "agencia/whatsapp-status/",
        agencia_views.WhatsAppStatusView.as_view(),
        name="whatsapp_status",
    ),
    path(
        "agencia/configuracion/motor-pdf/", agencia_views.MotorPdfView.as_view(), name="motor_pdf"
    ),
    path(
        "agencia/usuarios/", agencia_views.AgenciaUsersListView.as_view(), name="agencia_usuarios"
    ),
    path(
        "agencia/usuarios/nuevo/",
        agencia_views.UsuarioAgenciaCreateView.as_view(),
        name="usuario_create",
    ),
    path(
        "agencia/usuarios/<int:pk>/cambiar-estado/",
        agencia_views.UsuarioAgenciaToggleStatusView.as_view(),
        name="usuario_toggle",
    ),
    path(
        "agencia/usuarios/<int:pk>/cambiar-rol/",
        agencia_views.UsuarioAgenciaUpdateRoleView.as_view(),
        name="usuario_update_role",
    ),
    path(
        "agencia/auditoria/",
        audit_views_frontend.AgenciaAuditLogListView.as_view(),
        name="agencia_auditoria",
    ),
    path("agencia/cambiar/", agencia_views.CambiarAgenciaView.as_view(), name="cambiar_agencia"),
    # Configuración / Perfil
    path("setup/perfil/", user_profile_views.UserProfileView.as_view(), name="user_profile"),
    path(
        "settings/branding/",
        settings_views.BrandingSettingsView.as_view(),
        name="settings_branding",
    ),
    # Cron Jobs
    path("api/cron/sincronizar-bcv/", cron_views.sincronizar_bcv_cron, name="cron_sincronizar_bcv"),
    path(
        "api/cron/recordatorios-pago/",
        cron_views.enviar_recordatorios_cron,
        name="cron_recordatorios",
    ),
    path("api/cron/cierre-mensual/", cron_views.cierre_mensual_cron, name="cron_cierre_mensual"),
    path(
        "api/cron/cargar-catalogos/", cron_views.cargar_catalogos_cron, name="cron_cargar_catalogos"
    ),
    path("api/cron/health/", cron_views.health_check, name="cron_health"),
    # Tools & Intelligence
    path("tools/traductor/", translator_views.TraductorView.as_view(), name="traductor_tool"),
    path("translator/", include(("core.translator_urls", "translator"))),
    path(
        "intelligence/gds-analyzer/",
        intelligence_views.GDSAnalyzerView.as_view(),
        name="gds_analyzer",
    ),
    path(
        "intelligence/gds-analyzer/ajax/",
        intelligence_views.GDSAnalysisAjaxView.as_view(),
        name="gds_analyzer_ajax",
    ),
    path(
        "intelligence/gds-analyzer/inject/",
        intelligence_views.GDSInjectERPView.as_view(),
        name="gds_analyzer_inject",
    ),
    path(
        "intelligence/gds-analyzer/logo/<str:iata_code>.png",
        intelligence_views.AirlineLogoProxyView.as_view(),
        name="airline_logo_proxy",
    ),
    # Wiki
    path("wiki/gds/", wiki_views.wiki_gds_list, name="wiki_list"),
    path("wiki/gds/<str:category>/", wiki_views.wiki_gds_reader, name="wiki_reader"),
    path(
        "wiki/gds/<str:category>/<str:filename>/",
        wiki_views.wiki_gds_reader,
        name="wiki_reader_file",
    ),
    path("wiki/search/", wiki_views.wiki_search, name="wiki_search"),
    # God Mode
    path("god-mode/", god_mode_views.GodModeDashboardView.as_view(), name="god_mode"),
    path(
        "god-mode/impersonate/<int:agencia_id>/",
        god_mode_views.ImpersonateAgencyView.as_view(),
        name="god_mode_impersonate",
    ),
    path(
        "god-mode/stop-impersonate/",
        god_mode_views.StopImpersonateView.as_view(),
        name="god_mode_stop_impersonate",
    ),
    # Analytics & CEO
    path("ceo-dashboard/", dashboard.CEODashboardView.as_view(), name="ceo_dashboard"),
    path("api/ai-advisor/", dashboard.AIBusinessAdvisorView.as_view(), name="ai_business_advisor"),
    # Omnisearch
    # WhatsApp / Evolution
    path(
        "whatsapp/qr-img/<str:instance_name>/",
        evolution_qr_view.evolution_qr_proxy,
        name="evolution_qr_image",
    ),
    path(
        "whatsapp/qr/<str:instance_name>/",
        evolution_proxy_views.evolution_manager_proxy,
        name="evolution_qr_proxy",
    ),
    path(
        "whatsapp/qr/<str:instance_name>/<path:extra>",
        evolution_proxy_views.evolution_manager_proxy,
        name="evolution_qr_assets",
    ),
    # Health-check dedicado del flujo WhatsApp (sin auth, devuelve JSON)
    # Pensado para monitors externos (UptimeRobot, Prometheus blackbox, etc.)
    #
    # IMPORTANTE: Las rutas /alert/ y /alert/<slug>/ DEBEN ir ANTES de
    # /<slug>/ para evitar que Django matchee "alert" como instance_name.
    path(
        "whatsapp/health/",
        evolution_qr_view.whatsapp_qr_health,
        name="evolution_qr_health",
    ),
    path(
        "whatsapp/health/alert/",
        evolution_qr_view.whatsapp_health_alert_webhook,
        name="whatsapp_health_alert_webhook",
    ),
    path(
        "whatsapp/health/alert/<str:instance_name>/",
        evolution_qr_view.whatsapp_health_alert_webhook,
        name="whatsapp_health_alert_webhook_instance",
    ),
    # wildcard DEBE ir al final (lowest priority)
    path(
        "whatsapp/health/<str:instance_name>/",
        evolution_qr_view.whatsapp_qr_health,
        name="evolution_qr_health_instance",
    ),
    # Notificaciones & Monitor
    path("notifications/live/", notifications.notificaciones_live_view, name="notificaciones_live"),
    path(
        "notifications/panel/", notifications.notificaciones_panel_view, name="notificaciones_panel"
    ),
    path(
        "notifications/mark-read/",
        notifications.notificaciones_marcar_leidas_view,
        name="notificaciones_marcar_leidas",
    ),
    path(
        "notifications/badge/", notifications.notificaciones_badge_view, name="notificaciones_badge"
    ),
    path(
        "api/procesar-correos-boletos/",
        email_monitor_views.procesar_correos_boletos,
        name="procesar_correos_boletos",
    ),
    path(
        "api/webhooks/resend/inbound/",
        webhooks_views.ResendInboundWebhookView.as_view(),
        name="webhook_resend_inbound",
    ),
    # API Stats
    path("api/dashboard/stats/", dashboard_stats_api, name="dashboard_stats")
    if dashboard_stats_api
    else path(
        "api/dashboard/stats/", lambda r: JsonResponse({"error": "Not available"}, status=404)
    ),
    # --- INFRAESTRUCTURA Y SALUD ---
    path("health/", health_views.health_check, name="health_check"),
    path("health/metrics/", health_metrics_view, name="health_metrics"),
    path("csp-report/", csp_report_view, name="csp_report"),
    # --- DOCUMENTACIÓN API ---
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="core:schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="core:schema"), name="redoc"),
    # Magic Links
    path(
        "auth/magic-request/", auth_views.MagicLinkRequestView.as_view(), name="magic_link_request"
    ),
    path(
        "auth/magic/<str:token>/",
        auth_views.MagicLinkVerifyView.as_view(),
        name="magic_link_verify",
    ),
    # Billing / Account
    path("account/billing/", AccountBillingView.as_view(), name="account_billing"),
    # --- ERP BOLETOS INTELLIGENCE (MOVILIZADO AL FINAL PARA EVITAR SOBREESCRITURA) ---
    path("dashboard/modern/", DashboardView.as_view(), name="modern_dashboard"),
    path("dashboard/erp/auditoria/", erp_views.AuditoriaListView.as_view(), name="auditoria_list"),
    path(
        "dashboard/erp/comunicaciones/",
        erp_views.ComunicacionesListView.as_view(),
        name="comunicaciones_list",
    ),
    path(
        "dashboard/erp/boletos/", erp_views.DashboardBoletosView.as_view(), name="boletos_dashboard"
    ),
    path(
        "dashboard/erp/boletos/buscar/",
        erp_views.BoletosBusquedaView.as_view(),
        name="boletos_busqueda",
    ),
    path(
        "dashboard/erp/boletos/reportes/",
        erp_views.BoletosReportesView.as_view(),
        name="boletos_reportes",
    ),
    path(
        "dashboard/erp/boletos/reportes/exportar/",
        erp_views.ExportarBoletosExcelView.as_view(),
        name="boletos_reportes_exportar",
    ),
    path(
        "dashboard/erp/boletos/anulaciones/",
        erp_views.BoletosAnulacionesView.as_view(),
        name="boletos_anulaciones",
    ),
    path(
        "dashboard/erp/boletos/importar/",
        erp_views.BoletosImportarView.as_view(),
        name="boletos_importar",
    ),
    path(
        "dashboard/erp/boletos/manual/",
        erp_views.BoletosManualView.as_view(),
        name="boletos_manual",
    ),
    path(
        "api/boletos/dashboard-stats/",
        boleto_api_views.dashboard_stats,
        name="boletos_dashboard_stats",
    ),
    path("api/boletos/buscar/", boleto_api_views.buscar, name="boletos_buscar"),
    path("api/boletos/sin-venta/", boleto_api_views.boletos_sin_venta, name="boletos_sin_venta"),
    path(
        "api/boletos/<int:boleto_id>/reintentar-parseo/",
        boleto_api_views.reintentar_parseo,
        name="reintentar_parseo",
    ),
    path(
        "api/boletos/<int:boleto_id>/crear-venta/",
        boleto_api_views.crear_venta_desde_boleto,
        name="crear_venta_desde_boleto",
    ),
    path("api/boletos/upload/", BoletoUploadAPIView.as_view(), name="api_boleto_upload"),
    path("api/boletos/audit/", BoletoAuditAPIView.as_view(), name="api_boleto_audit"),
    path("api/boletos/<int:pk>/delete/", BoletoDeleteAPIView.as_view(), name="api_boleto_delete"),
    # UI Vistas de Revisión/Upload
    path("upload/boleto/", upload_views.UploadBoletoView.as_view(), name="upload_boleto"),
    path(
        "upload/boleto/<int:pk>/revisar/",
        upload_views.ReviewBoletoView.as_view(),
        name="revisar_boleto",
    ),
    path(
        "upload/boleto/<int:pk>/status/",
        upload_views.BoletoStatusView.as_view(),
        name="boleto_status",
    ),
    path(
        "upload/boleto/<int:pk>/pdf-status/",
        upload_views.BoletoPdfStatusView.as_view(),
        name="boleto_pdf_status",
    ),
    path(
        "upload/boleto/<int:pk>/desasociar-venta/",
        upload_views.DesasociarVentaView.as_view(),
        name="desasociar_venta",
    ),
    path(
        "upload/boleto/<int:pk>/eliminar-hard/",
        upload_views.eliminar_boleto,
        name="eliminar_boleto_hard",
    ),
    # Aliases para compatibilidad con templates ERP
    path("ventas/<int:pk>/editar/", VentaUpdateView.as_view(), name="editar_venta"),
    path(
        "ventas/<int:pk>/eliminar-permanente/",
        VentaDeleteView.as_view(),
        name="venta_eliminar_permanente",
    ),
    path(
        "api/boletos/<int:boleto_id>/reintentar-fast/",
        api_reintentar_parseo,
        name="api_boleto_retry",
    ),
    path("api/ventas/<int:venta_id>/generar-voucher/", generar_voucher, name="generar_voucher"),
    path("ventas/<int:pk>/facturar/", generar_factura_desde_venta, name="venta_facturar"),
    path("facturacion/<int:pk>/", FacturaDetailView.as_view(), name="factura_detalle"),
    path("facturacion/<int:pk>/pdf/", descargar_pdf_factura, name="factura_pdf"),
    path("facturacion/<int:pk>/emitir/", emitir_factura_definitiva, name="factura_emitir"),
    path("cotizaciones/nueva/", CotizacionCreateView.as_view(), name="cotizacion_nueva"),
    path("cotizaciones/<int:pk>/", CotizacionDetailView.as_view(), name="cotizacion_detalle"),
    path("cotizaciones/<int:pk>/editar/", CotizacionUpdateView.as_view(), name="cotizacion_editar"),
    path(
        "cotizaciones/<int:pk>/cambiar-estado/",
        CotizacionStatusView.as_view(),
        name="cotizacion_cambiar_estado",
    ),
    path("cotizaciones/<int:pk>/pdf/", CotizacionPDFView.as_view(), name="cotizacion_pdf"),
    path(
        "cotizaciones/<int:pk>/convertir/",
        CotizacionConvertirView.as_view(),
        name="cotizacion_convertir",
    ),
    # Listado de usuarios (Alias)
    path("agencia/usuarios/", agencia_views.AgenciaUsersListView.as_view(), name="usuarios_list"),
    # Reportes Contables
    path("api/reportes/libro-diario/", reportes_views.libro_diario, name="libro_diario"),
    path(
        "api/reportes/balance-comprobacion/",
        reportes_views.balance_comprobacion,
        name="balance_comprobacion",
    ),
    path(
        "api/reportes/estado-resultados/",
        reportes_views.estado_resultados,
        name="estado_resultados",
    ),
    path("api/reportes/validar-cuadre/", reportes_views.validar_cuadre, name="validar_cuadre"),
    path("api/reportes/exportar-excel/", reportes_views.exportar_excel, name="exportar_excel"),
    # Analytics y Pestañas HTMX
    path(
        "analytics/", dashboard_views.AnalyticsDashboardView.as_view(), name="analytics_dashboard"
    ),
    path("analytics/sales/", sales_analytics.sales_analytics_view, name="analytics_sales"),
    path("analytics/finance/", finance_analytics.finance_analytics_view, name="analytics_finance"),
    path("analytics/ops/", ops_analytics.ops_analytics_view, name="analytics_ops"),
    # Hoteles y Alojamientos
    path("hoteles/", HotelListView.as_view(), name="hotel_search"),
    path("hoteles/<slug:slug>/", HotelDetailView.as_view(), name="hotel_detail"),
    path("hoteles/<slug:slug>/story/", download_story_view, name="hotel_story"),
    path("api/hotels/quote/", HotelQuoteAPI.as_view(), name="hotel_quote_api"),
    # Vuelos
    path("flights/", FlightSearchView.as_view(), name="flight_search"),
    # Marketing y Generación IA
    path("api/marketing/generate-copy/", GenerateCopyAPI.as_view(), name="generate_copy_api"),
    path("marketing/hub/", MarketingHubView.as_view(), name="marketing_hub"),
    path("", include("apps.common.urls_core")),
]

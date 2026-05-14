from django.urls import path, include
from django.http import JsonResponse
from .views import (
    agencia_views, audit_views_frontend, user_profile_views,
    cron_views, dashboard, evolution_qr_view, evolution_proxy_views,
    fix_user_view, email_monitor_views, god_mode_views,
    intelligence_views, migration_api, notifications,
    search_views, settings_views, translator_views, webhooks_views, wiki_views,
    health_views
)
from core.middleware import csp_report_view
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from apps.marketing.views.marketing_views import MarketingHubView, GenerateAIImageView
from core.dashboard_stats import get_dashboard_stats as dashboard_stats_api

app_name = 'system'

urlpatterns = [
    # Configuración Agencia
    path('agencia/configuracion/', agencia_views.AgenciaSettingsView.as_view(), name='agencia_settings'), 
    path('agencia/whatsapp-status/', agencia_views.WhatsAppStatusView.as_view(), name='whatsapp_status'),
    path('agencia/configuracion/motor-pdf/', agencia_views.MotorPdfView.as_view(), name='motor_pdf'), 
    path('agencia/usuarios/', agencia_views.AgenciaUsersListView.as_view(), name='agencia_usuarios'),
    path('agencia/usuarios/nuevo/', agencia_views.UsuarioAgenciaCreateView.as_view(), name='usuario_create'),
    path('agencia/usuarios/<int:pk>/cambiar-estado/', agencia_views.UsuarioAgenciaToggleStatusView.as_view(), name='usuario_toggle'),
    path('agencia/usuarios/<int:pk>/cambiar-rol/', agencia_views.UsuarioAgenciaUpdateRoleView.as_view(), name='usuario_update_role'),
    path('agencia/auditoria/', audit_views_frontend.AgenciaAuditLogListView.as_view(), name='agencia_auditoria'),
    
    # Configuración / Perfil
    path('setup/perfil/', user_profile_views.UserProfileView.as_view(), name='user_profile'),
    path('settings/branding/', settings_views.BrandingSettingsView.as_view(), name='settings_branding'),

    # Cron Jobs
    path('api/cron/sincronizar-bcv/', cron_views.sincronizar_bcv_cron, name='cron_sincronizar_bcv'),
    path('api/cron/recordatorios-pago/', cron_views.enviar_recordatorios_cron, name='cron_recordatorios'),
    path('api/cron/cierre-mensual/', cron_views.cierre_mensual_cron, name='cron_cierre_mensual'),
    path('api/cron/cargar-catalogos/', cron_views.cargar_catalogos_cron, name='cron_cargar_catalogos'),
    path('api/cron/health/', cron_views.health_check, name='cron_health'),
    
    # Tools & Intelligence
    path('tools/traductor/', translator_views.TraductorView.as_view(), name='traductor_tool'),
    path('intelligence/gds-analyzer/', intelligence_views.GDSAnalyzerView.as_view(), name='gds_analyzer'),
    path('intelligence/gds-analyzer/ajax/', intelligence_views.GDSAnalysisAjaxView.as_view(), name='gds_analyzer_ajax'),
    path('intelligence/gds-analyzer/inject/', intelligence_views.GDSInjectERPView.as_view(), name='gds_analyzer_inject'),
    
    # Wiki
    path('wiki/gds/', wiki_views.wiki_gds_list, name='wiki_list'),
    path('wiki/gds/<str:category>/', wiki_views.wiki_gds_reader, name='wiki_reader'),
    path('wiki/gds/<str:category>/<str:filename>/', wiki_views.wiki_gds_reader, name='wiki_reader_file'),

    # God Mode
    path('god-mode/', god_mode_views.GodModeDashboardView.as_view(), name='god_mode'),
    path('god-mode/impersonate/<int:agencia_id>/', god_mode_views.ImpersonateAgencyView.as_view(), name='god_mode_impersonate'),
    path('god-mode/stop-impersonate/', god_mode_views.StopImpersonateView.as_view(), name='god_mode_stop_impersonate'),

    # Analytics & CEO
    path('ceo-dashboard/', dashboard.CEODashboardView.as_view(), name='ceo_dashboard'),
    path('api/ai-advisor/', dashboard.AIBusinessAdvisorView.as_view(), name='ai_business_advisor'),

    # Omnisearch
    path('omnisearch/', search_views.GlobalOmnisearchView.as_view(), name='omnisearch'),
    
    # WhatsApp / Evolution
    path('whatsapp/qr-img/<str:instance_name>/', evolution_qr_view.evolution_qr_proxy, name='evolution_qr_image'),
    path('whatsapp/qr/<str:instance_name>/', evolution_proxy_views.evolution_manager_proxy, name='evolution_qr_proxy'),
    path('whatsapp/qr/<str:instance_name>/<path:extra>', evolution_proxy_views.evolution_manager_proxy, name='evolution_qr_assets'),

    # Notificaciones & Monitor
    path('notifications/live/', notifications.notificaciones_live_view, name='notificaciones_live'),
    path('api/procesar-correos-boletos/', email_monitor_views.procesar_correos_boletos, name='procesar_correos_boletos'),
    path('api/webhooks/resend/inbound/', webhooks_views.ResendInboundWebhookView.as_view(), name='webhook_resend_inbound'),
    
    # API Stats
    path('api/dashboard/stats/', dashboard_stats_api, name='dashboard_stats') if dashboard_stats_api else path('api/dashboard/stats/', lambda r: JsonResponse({'error': 'Not available'}, status=404)),

    # --- INFRAESTRUCTURA Y SALUD ---
    path('health/', health_views.health_check, name='health_check'),
    path('csp-report/', csp_report_view, name='csp_report'),
    
    # --- DOCUMENTACIÓN API ---
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

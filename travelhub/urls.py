import logging

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import RedirectView, TemplateView
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.bookings.views.billing_api import (
    CheckoutPlanAPIView,
    CurrentBillingPlanAPIView,
    RegisterTenantAPIView,
)
from apps.bookings.views.comunicacion_views import generate_ical_calendar
from apps.bookings.views.itinerary_views import public_itinerary_view
from apps.communications.views.push_views import push_subscribe, push_unsubscribe
from core.metrics import health_metrics_view
from core.middleware import csp_report_view
from core.sso.views import sso_callback, sso_login
from core.views.auditoria_views import api_audit_logs
from core.views.auth_views import MagicLinkRequestView, MagicLinkVerifyView, TokenLogoutView
from core.views.dev_portal_views import developer_portal
from core.views.docs_views import docs_index, docs_page, public_manual
from core.views.evolution_proxy_views import evolution_manager_proxy
from core.views.health_views import health_check
from core.views.marketing_views import (
    demo_page,
    demo_request,
    lead_magnet_download,
    parse_demo,
    public_landing,
    public_pricing,
)
from core.views.ocr_views import OCRPassportView
from core.views.onboarding_views import OnboardingAgencyView, SaaSOnboardingView
from core.views.pwa_views import manifest, offline, service_worker
from core.views.status_views import status_api, status_page


def favicon_view(request):
    """favicon_view."""
    from django.shortcuts import redirect

    return redirect("/static/images/Logo TravelHub.png")


logger = logging.getLogger(__name__)


def _protect_docs(view):
    """_protect_docs."""
    if not settings.DEBUG:
        return staff_member_required(view)
    return view


# NOTA: En el enrutador maestro NO se declara app_name.
# El app_name = 'bookings' debe ir EXCLUSIVAMENTE en apps/bookings/urls.py

urlpatterns = [
    # --- CSP REPORT ---
    path("csp-report/", csp_report_view, name="csp_report"),
    # --- FAVICON ---
    re_path(r"^favicon\.ico$", favicon_view),
    # --- ADMINISTRACIÓN Y AUTENTICACIÓN ---
    path("admin/custom/", include("apps.common.urls_admin")),
    path("admin/custom/finance/", include("apps.finance.urls_admin")),
    path("admin/custom/bookings/", include("apps.bookings.urls_admin")),
    path("admin/custom/core/", include("core.urls_admin")),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("login/", ensure_csrf_cookie(auth_views.LoginView.as_view()), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("api/auth/jwt/obtain/", TokenObtainPairView.as_view(), name="jwt_obtain_pair"),
    path("api/auth/jwt/logout/", TokenLogoutView.as_view(), name="jwt_logout"),
    path("api/auth/register-tenant/", RegisterTenantAPIView.as_view(), name="register_tenant"),
    path(
        "api/billing/current-plan/",
        CurrentBillingPlanAPIView.as_view(),
        name="billing_current_plan",
    ),
    path("api/billing/checkout/", CheckoutPlanAPIView.as_view(), name="billing_checkout"),
    # Magic Links
    path("auth/magic-request/", MagicLinkRequestView.as_view(), name="magic_link_request"),
    path("auth/magic/<str:token>/", MagicLinkVerifyView.as_view(), name="magic_link_verify"),
    # --- ONBOARDING (SaaS) ---
    path("onboarding/", SaaSOnboardingView.as_view(), name="onboarding_start"),
    path("onboarding/agency/", OnboardingAgencyView.as_view(), name="onboarding_agency"),
    path("onboarding/", include("apps.common.urls_onboarding")),
    # --- INCLUSIÓN DE MÓDULOS ---
    path("bookings/", include("apps.bookings.urls")),
    path("finance/", include("apps.finance.urls")),
    path("crm/", include("apps.crm.urls")),
    path("system/", include(("core.urls_system", "core"))),
    path("accounting/", include("apps.contabilidad.urls")),
    path("cms/", include("apps.cms.urls")),
    path("gamification/", include("apps.gamification.urls")),
    path("reports/", include("apps.reports.urls")),
    path("tasks/", include("apps.tasks.urls")),
    path("marketing/", include("apps.marketing.urls")),
    path("cotizaciones/", include("apps.cotizaciones.urls")),
    # --- API UNIFICADA (DRY: una sola inclusión) ---
    path("api/", include("travelhub.urls_api")),
    # --- INLINE API ROUTES ---
    path("api/schema/", _protect_docs(SpectacularAPIView.as_view()), name="schema"),
    path(
        "api/docs/",
        _protect_docs(SpectacularSwaggerView.as_view(url_name="schema")),
        name="swagger-ui-direct",
    ),
    path(
        "api/redoc/",
        _protect_docs(SpectacularRedocView.as_view(url_name="schema")),
        name="redoc-direct",
    ),
    path("api/audit-logs/", api_audit_logs, name="api_audit_logs"),
    path("api/parse-demo/", parse_demo, name="parse_demo"),
    path("api/lead-magnet/", lead_magnet_download, name="lead_magnet_download"),
    path("api/push/subscribe/", push_subscribe, name="push_subscribe"),
    path("api/push/unsubscribe/", push_unsubscribe, name="push_unsubscribe"),
    # OCR & ID Scanner endpoints
    path("api/crm/cedula-scanner/", OCRPassportView.as_view(), name="api_cedula_scanner"),
    path("api/ocr/passport/", OCRPassportView.as_view(), name="ocr_passport"),
    path("api/ocr/scan-id/", OCRPassportView.as_view(), name="api_scan_id"),
    # Public routes (no /api/ prefix) for external consumers
    path("schema/", _protect_docs(SpectacularAPIView.as_view()), name="schema_root"),
    path(
        "redoc/", _protect_docs(SpectacularRedocView.as_view(url_name="schema_root")), name="redoc"
    ),
    # Developer Portal
    path("developers/", developer_portal, name="developer_portal"),
    # Public Passenger Itinerary Live Portal & Calendar (RFC 5545 iCal)
    path("itinerary/v1/live/<str:token>/", public_itinerary_view, name="public_itinerary_root"),
    path(
        "itinerary/v1/live/<str:token>/calendar.ics",
        generate_ical_calendar,
        name="public_itinerary_calendar_ics_root",
    ),
    # --- DASHBOARD PRINCIPAL & ACCESOS ---
    path("", public_landing, name="home"),
    path(
        "dashboard/",
        RedirectView.as_view(pattern_name="bookings:modern_dashboard", permanent=False),
        name="dashboard_root",
    ),
    path(
        "mensajes/",
        RedirectView.as_view(pattern_name="crm:inbox", permanent=False),
        name="mensajes_root",
    ),
    path(
        "inbox/",
        RedirectView.as_view(pattern_name="crm:inbox", permanent=False),
        name="inbox_root",
    ),
    path("prometheus/", include("django_prometheus.urls")),
    path("health/", health_check, name="health"),
    path("health/metrics/", health_metrics_view, name="health_metrics"),
    # PWA
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path(
        "sitemap.xml",
        TemplateView.as_view(template_name="sitemap.xml", content_type="application/xml"),
    ),
    path("manifest.json", manifest, name="pwa_manifest"),
    path("service-worker.js", service_worker, name="service_worker"),
    path("offline/", offline, name="offline"),
    # Proxy para Evolution Manager (requiere estar en la raíz para que React Router funcione)
    path("manager/qr/<str:instance_name>/", evolution_manager_proxy, name="evolution_manager_root"),
    path(
        "manager/qr/<str:instance_name>/<path:extra>",
        evolution_manager_proxy,
        name="evolution_manager_assets",
    ),
    # Status Page (solo staff)
    path("status/", _protect_docs(status_page), name="status_page"),
    path("status/api/", _protect_docs(status_api), name="status_api"),
    # Knowledge Base
    path("docs/", _protect_docs(docs_index), name="docs_index"),
    path("docs/<path:path>/", _protect_docs(docs_page), name="docs_page"),
    # Manual de usuario público
    path("manual/", public_manual, name="public_manual"),
    # Public Marketing
    path("pricing/", public_pricing, name="public_pricing"),
    path("demo/", demo_page, name="demo_page"),
    path("api/demo-request/", demo_request, name="demo_request"),
    # SSO / SAML / OIDC
    path("sso/login/<int:provider_id>/", sso_login, name="sso_login"),
    path("sso/callback/<int:provider_id>/", sso_callback, name="sso_callback"),
    # --- INTERNACIONALIZACIÓN (i18n) ---
    path("i18n/", include("django.conf.urls.i18n")),
]


# Servir media en desarrollo local o cuando R2 está desactivado (USE_R2=False).
# En producción con R2 activo, Cloudflare sirve los archivos directamente —
# no es necesario (ni deseable) que Django/Gunicorn los sirva.
if settings.DEBUG or not getattr(settings, "USE_R2", True):
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

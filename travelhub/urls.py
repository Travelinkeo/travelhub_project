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

from apps.communications.views.push_views import push_subscribe, push_unsubscribe
from core.metrics import health_metrics_view
from core.middleware import csp_report_view
from core.sso.views import sso_callback, sso_login
from core.views.auditoria_views import api_audit_logs
from core.views.auth_views import MagicLinkRequestView, MagicLinkVerifyView, TokenLogoutView
from core.views.dev_portal_views import developer_portal
from core.views.docs_views import docs_index, docs_page, public_manual
from core.views.health_views import health_check
from core.views.marketing_views import (
    lead_magnet_download,
    parse_demo,
    public_landing,
    public_pricing,
)
from core.views.onboarding_views import OnboardingAgencyView, SaaSOnboardingView
from core.views.pwa_views import manifest, offline, service_worker
from core.views.status_views import status_api, status_page


def favicon_view(request):
    from django.shortcuts import redirect

    return redirect("/static/images/Logo TravelHub.png")


logger = logging.getLogger(__name__)


def _protect_docs(view):
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
    path("admin/", admin.site.urls),  # <-- Faltaba tu panel de admin
    path("accounts/", include("django.contrib.auth.urls")),  # <-- Faltaban las rutas base de auth
    path("login/", ensure_csrf_cookie(auth_views.LoginView.as_view()), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("api/auth/jwt/obtain/", TokenObtainPairView.as_view(), name="jwt_obtain_pair"),
    path("api/auth/jwt/logout/", TokenLogoutView.as_view(), name="jwt_logout"),
    # Magic Links
    path("auth/magic-request/", MagicLinkRequestView.as_view(), name="magic_link_request"),
    path("auth/magic/<str:token>/", MagicLinkVerifyView.as_view(), name="magic_link_verify"),
    # --- ONBOARDING (SaaS) ---
    path("onboarding/", SaaSOnboardingView.as_view(), name="onboarding_start"),
    path("onboarding/agency/", OnboardingAgencyView.as_view(), name="onboarding_agency"),
    path("onboarding/", include("apps.common.urls_onboarding")),
    # --- INCLUSIÓN DE MÓDULOS (ESTO SOLUCIONA EL ERROR NOREVERSEMATCH) ---
    path("bookings/", include("apps.bookings.urls")),
    path("finance/", include("apps.finance.urls")),
    path("crm/", include("apps.crm.urls")),
    path("system/", include(("core.urls_system", "core"))),
    path("accounting/", include("apps.contabilidad.urls")),
    path("cms/", include("apps.cms.urls")),
    path("gamification/", include("apps.gamification.urls")),
    path("reports/", include("apps.reports.urls")),
    path("marketing/", include("apps.marketing.urls")),
    path("cotizaciones/", include("apps.cotizaciones.urls")),
    path("api/", include("travelhub.urls_api")),
    path("api/v1/", include("travelhub.urls_api")),
    path("core/api/", include("travelhub.urls_api")),
    # --- INLINE API ROUTES (disponibles bajo /api/ y /api/v1/) ---
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
    path("api/v1/schema/", _protect_docs(SpectacularAPIView.as_view()), name="schema_v1"),
    path(
        "api/v1/docs/",
        _protect_docs(SpectacularSwaggerView.as_view(url_name="schema_v1")),
        name="swagger-ui-v1",
    ),
    path(
        "api/v1/redoc/",
        _protect_docs(SpectacularRedocView.as_view(url_name="schema_v1")),
        name="redoc-v1",
    ),
    path("api/v1/audit-logs/", api_audit_logs, name="api_audit_logs_v1"),
    path("api/v1/parse-demo/", parse_demo, name="parse_demo_v1"),
    path("api/v1/lead-magnet/", lead_magnet_download, name="lead_magnet_download_v1"),
    path("api/v1/push/subscribe/", push_subscribe, name="push_subscribe_v1"),
    path("api/v1/push/unsubscribe/", push_unsubscribe, name="push_unsubscribe_v1"),
    # Public routes (no /api/ prefix) for external consumers
    path("schema/", _protect_docs(SpectacularAPIView.as_view()), name="schema_root"),
    path(
        "redoc/", _protect_docs(SpectacularRedocView.as_view(url_name="schema_root")), name="redoc"
    ),
    # Developer Portal
    path("developers/", developer_portal, name="developer_portal"),
    # --- DASHBOARD PRINCIPAL ---
    # Landing page pública — si autenticado, redirige al dashboard
    path("", public_landing, name="home"),
    path(
        "dashboard/",
        RedirectView.as_view(pattern_name="bookings:modern_dashboard", permanent=False),
        name="dashboard_root",
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
    # Status Page (solo staff)
    path("status/", _protect_docs(status_page), name="status_page"),
    path("status/api/", _protect_docs(status_api), name="status_api"),
    # Knowledge Base — documentación técnica (solo staff)
    path("docs/", _protect_docs(docs_index), name="docs_index"),
    path("docs/<path:path>/", _protect_docs(docs_page), name="docs_page"),
    # Manual de usuario público
    path("manual/", public_manual, name="public_manual"),
    # Public Marketing
    path("pricing/", public_pricing, name="public_pricing"),
    # SSO / SAML / OIDC
    path("sso/login/<int:provider_id>/", sso_login, name="sso_login"),
    path("sso/callback/<int:provider_id>/", sso_callback, name="sso_callback"),
    # --- INTERNACIONALIZACIÓN (i18n) ---
    path("i18n/", include("django.conf.urls.i18n")),  # Provee /i18n/set_language/
]


# Servir media en desarrollo local o cuando R2 está desactivado (USE_R2=False).
# En producción con R2 activo, Cloudflare sirve los archivos directamente —
# no es necesario (ni deseable) que Django/Gunicorn los sirva.
if settings.DEBUG or not getattr(settings, "USE_R2", True):
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

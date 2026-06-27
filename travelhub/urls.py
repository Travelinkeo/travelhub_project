import logging

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import RedirectView
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView

from core.metrics import health_metrics_view
from core.middleware import csp_report_view
from core.views.auditoria_views import api_audit_logs
from core.views.auth_views import MagicLinkRequestView, MagicLinkVerifyView, TokenLogoutView
from core.views.onboarding_views import OnboardingAgencyView, SaaSOnboardingView


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
    # Audit Logs
    path("api/audit-logs/", api_audit_logs, name="api_audit_logs"),
    # Magic Links
    path("auth/magic-request/", MagicLinkRequestView.as_view(), name="magic_link_request"),
    path("auth/magic/<str:token>/", MagicLinkVerifyView.as_view(), name="magic_link_verify"),
    # --- ONBOARDING (SaaS) ---
    path("onboarding/", SaaSOnboardingView.as_view(), name="onboarding_start"),
    path("onboarding/agency/", OnboardingAgencyView.as_view(), name="onboarding_agency"),
    # --- INCLUSIÓN DE MÓDULOS (ESTO SOLUCIONA EL ERROR NOREVERSEMATCH) ---
    path("bookings/", include("apps.bookings.urls")),
    path("finance/", include("apps.finance.urls")),
    path("crm/", include("apps.crm.urls")),
    path("system/", include(("core.urls_system", "core"))),
    path("accounting/", include("apps.contabilidad.urls")),
    path("cms/", include("apps.cms.urls")),
    path("marketing/", include("apps.marketing.urls")),
    path("cotizaciones/", include("apps.cotizaciones.urls")),
    path("api/", include("travelhub.urls_api")),
    # --- DOCUMENTACIÓN API (PROTEGIDA EN PRODUCCIÓN) ---
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
    # Public routes (no /api/ prefix) for external consumers
    path("schema/", _protect_docs(SpectacularAPIView.as_view()), name="schema_root"),
    path(
        "docs/",
        _protect_docs(SpectacularSwaggerView.as_view(url_name="schema_root")),
        name="swagger-ui",
    ),
    path(
        "redoc/", _protect_docs(SpectacularRedocView.as_view(url_name="schema_root")), name="redoc"
    ),
    # --- DASHBOARD PRINCIPAL ---
    # Redirige a la vista modern_dashboard que ahora reside en bookings
    path(
        "",
        RedirectView.as_view(pattern_name="bookings:modern_dashboard", permanent=False),
        name="home",
    ),
    path(
        "dashboard/",
        RedirectView.as_view(pattern_name="bookings:modern_dashboard", permanent=False),
        name="dashboard_root",
    ),
    path("prometheus/", include("django_prometheus.urls")),
    path("health/metrics/", health_metrics_view, name="health_metrics"),
]


# Servir media en desarrollo local o cuando R2 está desactivado (USE_R2=False).
# En producción con R2 activo, Cloudflare sirve los archivos directamente —
# no es necesario (ni deseable) que Django/Gunicorn los sirva.
if settings.DEBUG or not getattr(settings, "USE_R2", True):
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

import logging

from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import TokenObtainPairView

from core.views.auth_views import MagicLinkRequestView, MagicLinkVerifyView, TokenLogoutView
from core.views.marketing_views import lead_magnet_download, parse_demo
from core.views.onboarding_views import OnboardingAgencyView, SaaSOnboardingView
from core.views.onboarding_wizard_views import OnboardingWizardView
from core.views.portal_views import PortalHomeView, PortalLookupView, PortalTokenRedirectView
from core.views.webhooks_views_ui import WebhookDeliveryListView, WebhookListView

logger = logging.getLogger(__name__)
app_name = "core"

urlpatterns = [
    # --- MARKETING & DEMO ---
    path("api/parse-demo/", parse_demo, name="parse_demo"),
    path("api/lead-magnet/", lead_magnet_download, name="lead_magnet_download"),
    # --- ADMINISTRACIÓN Y AUTENTICACIÓN ---
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("api/auth/jwt/obtain/", TokenObtainPairView.as_view(), name="jwt_obtain_pair"),
    path("api/auth/jwt/logout/", TokenLogoutView.as_view(), name="jwt_logout"),
    # Magic Links
    path("auth/magic-request/", MagicLinkRequestView.as_view(), name="magic_link_request"),
    path("auth/magic/<str:token>/", MagicLinkVerifyView.as_view(), name="magic_link_verify"),
    # --- ONBOARDING (SaaS) ---
    path("onboarding/", SaaSOnboardingView.as_view(), name="onboarding_start"),
    path("onboarding/agency/", OnboardingAgencyView.as_view(), name="onboarding_agency"),
    path("onboarding/wizard/", OnboardingWizardView.as_view(), name="onboarding_wizard"),
    # --- WEBHOOKS ---
    path("webhooks/", WebhookListView.as_view(), name="webhooks_list"),
    path(
        "webhooks/<int:webhook_id>/deliveries/",
        WebhookDeliveryListView.as_view(),
        name="webhooks_deliveries",
    ),
    # --- PORTAL DEL PASAJERO ---
    path("portal/", PortalHomeView.as_view(), name="portal_home"),
    path("portal/lookup/", PortalLookupView.as_view(), name="portal_lookup"),
    path(
        "portal/r/<uuid:uuid_token>/",
        PortalTokenRedirectView.as_view(),
        name="portal_token_redirect",
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
]

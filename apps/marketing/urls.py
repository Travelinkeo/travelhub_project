"""Configuración de rutas (URLs) para la aplicación marketing.
"""

from django.urls import path

from apps.marketing.views.dashboard_views import MarketingDashboardView
from apps.marketing.views.generation_views import (
    AIForecastView,
    GenerarCopyView,
    GenerarFlyerView,
    GenerarSocialMediaAdvancedView,
    MarketingFeedView,
)
from apps.marketing.views.social_views import SocialHubView

app_name = "marketing"

urlpatterns = [
    path("dashboard/", MarketingDashboardView.as_view(), name="dashboard"),
    path("generar-flyer/", GenerarFlyerView.as_view(), name="generar_flyer"),
    path("generar-copy/", GenerarCopyView.as_view(), name="generar_copy"),
    path(
        "api/generate-social-advanced/",
        GenerarSocialMediaAdvancedView.as_view(),
        name="generar_social_advanced",
    ),
    path("api/marketing-feed/", MarketingFeedView.as_view(), name="marketing_feed"),
    path("social-hub/", SocialHubView.as_view(), name="social_hub"),
    path("forecast/", AIForecastView.as_view(), name="forecast"),
]

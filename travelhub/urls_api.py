# travelhub/urls_api.py
import logging

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

logger = logging.getLogger(__name__)

# Router principal (v1)
router = DefaultRouter()

# 1. Bookings Router
try:
    from apps.bookings.urls import router as bookings_router

    for prefix, viewset, basename in bookings_router.registry:
        if prefix not in [r[0] for r in router.registry]:
            router.register(prefix, viewset, basename=basename)
    logger.info("Successfully merged Bookings router into global API")
except Exception as e:
    logger.error(f"Error merging Bookings router: {e}")

# 2. CRM Router
try:
    from apps.crm.urls import router as crm_router

    for prefix, viewset, basename in crm_router.registry:
        if prefix not in [r[0] for r in router.registry]:
            router.register(prefix, viewset, basename=basename)
    logger.info("Successfully merged CRM router into global API")
except Exception as e:
    logger.error(f"Error merging CRM router: {e}")

# 3. Finance Router
try:
    from apps.finance.urls import router as finance_router

    for prefix, viewset, basename in finance_router.registry:
        clean_prefix = prefix[4:] if prefix.startswith("api/") else prefix
        if clean_prefix not in [r[0] for r in router.registry]:
            router.register(clean_prefix, viewset, basename=basename)
    logger.info("Successfully merged Finance router into global API")
except Exception as e:
    logger.error(f"Error merging Finance router: {e}")

# API v1 patterns
urlpatterns = [
    # Router principal
    path("", include(router.urls)),
    # Boleto Status API (P3-002)
    path("boletos/<int:pk>/status/", include("apps.bookings.urls")),
    # Schema & Docs
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# For backward compatibility, also expose at /api/v1/ via travelhub/urls.py

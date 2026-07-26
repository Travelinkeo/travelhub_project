# travelhub/urls_api.py
import logging

from rest_framework.routers import DefaultRouter

logger = logging.getLogger(__name__)

router = DefaultRouter()

# 1. Bookings Router
try:
    from apps.bookings.urls import router as bookings_router

    for prefix, viewset, basename in bookings_router.registry:
        # Avoid duplicate registration
        if prefix not in [r[0] for r in router.registry]:
            router.register(prefix, viewset, basename=basename)
    logger.info("Successfully merged Bookings router into global API")
except Exception as e:
    logger.error(f"Error merging Bookings router: {e}")

# 2. CRM Router
try:
    from apps.crm.urls import router as crm_router

    for prefix, viewset, basename in crm_router.registry:
        # Avoid duplicate registration
        if prefix not in [r[0] for r in router.registry]:
            router.register(prefix, viewset, basename=basename)
    logger.info("Successfully merged CRM router into global API")
except Exception as e:
    logger.error(f"Error merging CRM router: {e}")

# 3. Finance Router
try:
    from apps.finance.urls import router as finance_router

    for prefix, viewset, basename in finance_router.registry:
        # Strip api/ prefix from finance router prefixes if it exists (e.g. api/reconciliacion -> reconciliacion)
        clean_prefix = prefix[4:] if prefix.startswith("api/") else prefix
        # Avoid duplicate registration
        if clean_prefix not in [r[0] for r in router.registry]:
            router.register(clean_prefix, viewset, basename=basename)
    logger.info("Successfully merged Finance router into global API")
except Exception as e:
    logger.error(f"Error merging Finance router: {e}")

urlpatterns = router.urls

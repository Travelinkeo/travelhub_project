"""Rutas de la API REST — fusiona los routers de Bookings, CRM y Finance en un DefaultRouter global."""

import logging

from rest_framework.routers import DefaultRouter

logger = logging.getLogger(__name__)

# Crea el router global que unifica todos los endpoints de la API
router = DefaultRouter()

# 1. Bookings Router — registra vistas de reservas y boletos
try:
    from apps.bookings.urls import router as bookings_router

    for prefix, viewset, basename in bookings_router.registry:
        # Evita registros duplicados
        if prefix not in [r[0] for r in router.registry]:
            router.register(prefix, viewset, basename=basename)
    logger.info("Successfully merged Bookings router into global API")
except Exception as e:
    logger.error(f"Error merging Bookings router: {e}")

# 2. CRM Router — registra vistas de clientes, pasajeros y oportunidades
try:
    from apps.crm.urls import router as crm_router

    for prefix, viewset, basename in crm_router.registry:
        if prefix not in [r[0] for r in router.registry]:
            router.register(prefix, viewset, basename=basename)
    logger.info("Successfully merged CRM router into global API")
except Exception as e:
    logger.error(f"Error merging CRM router: {e}")

# 3. Finance Router — registra vistas de facturación, conciliación y liquidaciones
try:
    from apps.finance.urls import router as finance_router

    for prefix, viewset, basename in finance_router.registry:
        # Limpia prefijo api/ si existe
        clean_prefix = prefix[4:] if prefix.startswith("api/") else prefix
        if clean_prefix not in [r[0] for r in router.registry]:
            router.register(clean_prefix, viewset, basename=basename)
    logger.info("Successfully merged Finance router into global API")
except Exception as e:
    logger.error(f"Error merging Finance router: {e}")

urlpatterns = router.urls

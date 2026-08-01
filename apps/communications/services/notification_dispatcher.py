"""
Notification Dispatcher (Legacy Compatibility Layer)
====================================================

This module provides backward compatibility for legacy notification functions.
All new code should use `apps.communications.services.notification_router.notification_router`.

DEPRECATED: Use `apps.communications.services.notification_router.notification_router` instead.
"""

import logging
import warnings

from apps.communications.services.notification_router import (
    notificar_alerta_migratoria,
    notificar_boleto_procesado,
    # Legacy compat
    notificar_confirmacion_pago,
    notificar_confirmacion_venta,
    notificar_recordatorio_pago,
)

logger = logging.getLogger(__name__)

# Emit deprecation warning on import
warnings.warn(
    "notification_dispatcher is deprecated. Use notification_router instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export legacy functions for backward compatibility
__all__ = [
    "notificar_confirmacion_pago",
    "notificar_recordatorio_pago",
    "notificar_confirmacion_venta",
    "notificar_boleto_procesado",
    "notificar_alerta_migratoria",
]

# The actual implementations are in apps.communications.services.notification_router
# This file just re-exports them for backward compatibility

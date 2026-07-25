# Views package - Export active views

# Import specific views to expose them under core.views
"""Inicializador del paquete."""

from . import auth_views, erp_views, flights_views, inventario_views

__all__ = ["auth_views", "erp_views", "flights_views", "inventario_views"]

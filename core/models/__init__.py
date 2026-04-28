"""Punto de entrada de modelos (Fase 2 de modularización).

Carga modelos desde submódulos temáticos.
"""

# from core.middleware import SecurityHeadersMiddleware # REFACTOR: Mover a middleware.py
from core.models_catalogos import Aerolinea, Ciudad, ComisionProveedorServicio, Moneda, Pais, ProductoServicio, Proveedor, TipoCambio, TasaCambio
from core.validators import validar_no_vacio_o_espacios, validar_numero_pasaporte

# REFACTOR: Se eliminan imports directos de apps.* para romper ciclos masivos.
# Los modelos de apps (Bookings, Finance, CRM, Cotizaciones) deben consumirse desde sus propias apps
# o mediante referencias lazy 'app.Modelo'.

from .agencia import Agencia, UsuarioAgencia
from .migration_checks import MigrationCheck
from .audit import AuditLog
from .notificaciones import NotificacionInteligente
from .productos_terrestres import ProductoTerrestre

# Estos siguen en core por ahora (pendientes de fase final de migración total)
from .contabilidad import AsientoContable, DetalleAsiento, ItemLiquidacion, LiquidacionProveedor, PlanContable
from .cruceros import CruceroReserva
from .tarifario_hoteles import TarifarioProveedor, HotelTarifario, TipoHabitacion, TarifaHabitacion, Amenity, ImagenHotel
from .pasaportes import PasaporteEscaneado

from .facturacion_consolidada import (
    FacturaConsolidada,
    ItemFacturaConsolidada,
    DocumentoExportacionConsolidado
)

# --- CMS (Migrado a apps.cms) ---
# Se consumen directamente desde apps.cms.models

__all__ = [
    # Agencia
    'Agencia', 'UsuarioAgencia', 'NotificacionInteligente',
    'MigrationCheck', 'AuditLog',
    # Catálogos (Físicamente en core)
    'Pais', 'Ciudad', 'Moneda', 'TipoCambio', 'TasaCambio', 'Proveedor', 'ProductoServicio', 'Aerolinea', 'ComisionProveedorServicio',
    'ProductoTerrestre',
    # Contabilidad (Siguen en core temporalmente)
    'AsientoContable', 'PlanContable', 'DetalleAsiento', 'LiquidacionProveedor', 'ItemLiquidacion',
    # Otros
    'PasaporteEscaneado', 'CruceroReserva',
]

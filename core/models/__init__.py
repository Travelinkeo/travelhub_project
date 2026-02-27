"""Punto de entrada de modelos (Fase 2 de modularización).

Carga modelos desde submódulos temáticos.
"""

from core.middleware import SecurityHeadersMiddleware
from core.models_catalogos import Aerolinea, Ciudad, ComisionProveedorServicio, Moneda, Pais, ProductoServicio, Proveedor, TipoCambio
from core.validators import validar_no_vacio_o_espacios, validar_numero_pasaporte

from apps.bookings.models import (
    ActividadServicio,
    AlojamientoReserva,
    AlquilerAutoReserva,
    AuditLog,
    BoletoImportado,
    CircuitoDia,
    CircuitoTuristico,
    EventoServicio,
    FeeVenta,
    ItemVenta,
    PagoVenta,
    PaqueteAereo,
    SegmentoVuelo,
    ServicioAdicionalDetalle,
    SolicitudAnulacion,
    TrasladoServicio,
    Venta,
    VentaParseMetadata,
)
from apps.finance.models import (
    Factura,
    ItemFactura,
    ReporteProveedor,
    ItemReporte,
    DiferenciaFinanciera,
    GastoOperativo,
)
from apps.crm.models import Cliente, Pasajero
from cotizaciones.models import Cotizacion, ItemCotizacion
from .agencia import Agencia, UsuarioAgencia
from .migration_checks import MigrationCheck

# Estos siguen en core por ahora (pendientes de fase final de migración total)
from .contabilidad import AsientoContable, DetalleAsiento, ItemLiquidacion, LiquidacionProveedor, PlanContable
from .cruceros import CruceroReserva
from .tarifario_hoteles import TarifarioProveedor, HotelTarifario, TipoHabitacion, TarifaHabitacion, Amenity, ImagenHotel

from .facturacion_consolidada import (
    FacturaConsolidada,
    ItemFacturaConsolidada,
    DocumentoExportacionConsolidado
)

# --- CMS (Migrado a apps.cms) ---
from apps.cms.models import (
    Articulo as ArticuloBlog,
    GuiaDestino as DestinoCMS,
    PostRedesSociales as PaqueteTuristicoCMS,
)
# CMS Models migrados a apps/cms

__all__ = [
    # Agencia
    'Agencia', 'UsuarioAgencia',
    # Contabilidad
    'AsientoContable', 'PlanContable', 'DetalleAsiento', 'LiquidacionProveedor', 'ItemLiquidacion', 'GastoOperativo',
    # Ventas y Componentes
    'Venta', 'ItemVenta', 'AlojamientoReserva', 'TrasladoServicio', 'ActividadServicio', 'SegmentoVuelo',
    'FeeVenta', 'PagoVenta', 'AlquilerAutoReserva', 'EventoServicio', 'CircuitoTuristico', 'CircuitoDia',
    'PaqueteAereo', 'ServicioAdicionalDetalle', 'VentaParseMetadata', 'AuditLog', 'CruceroReserva',
    # Facturación Consolidada
    'FacturaConsolidada', 'ItemFacturaConsolidada', 'DocumentoExportacionConsolidado',
    # Boletos
    'BoletoImportado', 'SolicitudAnulacion',
    # CMS
    'DestinoCMS', 'PaqueteTuristicoCMS', 'ArticuloBlog',
    # Catálogos
    'Pais', 'Ciudad', 'Moneda', 'TipoCambio', 'Proveedor', 'ProductoServicio', 'Aerolinea', 'ComisionProveedorServicio',
    # Personas
    'Pasajero', 'Cliente', 'MigrationCheck',
    # Cotizaciones
    'Cotizacion', 'ItemCotizacion',
    # Tarifario Hoteles
    'TarifarioProveedor', 'HotelTarifario', 'TipoHabitacion', 'TarifaHabitacion', 'Amenity', 'ImagenHotel',
    # Middleware
    'RequestMetaAuditMiddleware', 'SecurityHeadersMiddleware',
    # Reconciliación
    'ReporteProveedor', 'ItemReporte',
]

"""Punto de entrada de modelos (Fase 2 de modularización).

Carga modelos desde submódulos temáticos.
"""

from core.middleware import RequestMetaAuditMiddleware, SecurityHeadersMiddleware
from core.models_catalogos import Aerolinea, Ciudad, Moneda, Pais, ProductoServicio, Proveedor, TipoCambio
from core.validators import validar_no_vacio_o_espacios, validar_numero_pasaporte

from .boletos import BoletoImportado
from .cms import (
    ArticuloBlog,
    DestinoCMS,
    FormularioContactoCMS,
    MenuItemCMS,
    PaginaCMS,
    PaqueteTuristicoCMS,
    Testimonio,
)
from .comunicaciones import ComunicacionProveedor
from .contabilidad import AsientoContable, DetalleAsiento, ItemLiquidacion, LiquidacionProveedor, PlanContable
from .cotizaciones import Cotizacion, ItemCotizacion
from .facturacion import Factura, ItemFactura
from .facturacion_venezuela import FacturaVenezuela, ItemFacturaVenezuela, DocumentoExportacion
from .personas import Cliente, Pasajero
from .ventas import (
    ActividadServicio,
    AlojamientoReserva,
    AlquilerAutoReserva,
    AuditLog,
    CircuitoDia,
    CircuitoTuristico,
    EventoServicio,
    FeeVenta,
    ItemVenta,
    PagoVenta,
    PaqueteAereo,
    SegmentoVuelo,
    ServicioAdicionalDetalle,
    TrasladoServicio,
    Venta,
    VentaParseMetadata,
)

__all__ = [
    # Contabilidad
    'AsientoContable', 'PlanContable', 'DetalleAsiento', 'LiquidacionProveedor', 'ItemLiquidacion',
    # Ventas y Componentes
    'Venta', 'ItemVenta', 'AlojamientoReserva', 'TrasladoServicio', 'ActividadServicio', 'SegmentoVuelo',
    'FeeVenta', 'PagoVenta', 'AlquilerAutoReserva', 'EventoServicio', 'CircuitoTuristico', 'CircuitoDia',
    'PaqueteAereo', 'ServicioAdicionalDetalle', 'VentaParseMetadata', 'AuditLog',
    # Facturación
    'Factura', 'ItemFactura', 'FacturaVenezuela', 'ItemFacturaVenezuela', 'DocumentoExportacion',
    # Boletos
    'BoletoImportado',
    'ComunicacionProveedor',
    # CMS
    'PaginaCMS', 'DestinoCMS', 'PaqueteTuristicoCMS', 'ArticuloBlog', 'Testimonio', 'MenuItemCMS', 'FormularioContactoCMS',
    # Catálogos
    'Pais', 'Ciudad', 'Moneda', 'TipoCambio', 'Proveedor', 'ProductoServicio', 'Aerolinea',
    # Personas
    'Pasajero', 'Cliente',
    # Cotizaciones
    'Cotizacion', 'ItemCotizacion',
    # Middleware
    'RequestMetaAuditMiddleware', 'SecurityHeadersMiddleware',
    # Validators (already in core.validators)
    'validar_no_vacio_o_espacios',
    'validar_numero_pasaporte',
]

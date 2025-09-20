"""Punto de entrada de modelos (Fase 2 de modularización).

Carga modelos desde submódulos temáticos.
"""

from core.middleware import RequestMetaAuditMiddleware, SecurityHeadersMiddleware
from core.models_catalogos import Ciudad, Moneda, Pais, ProductoServicio, Proveedor, TipoCambio
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
from .contabilidad import AsientoContable, DetalleAsiento, PlanContable
from .cotizaciones import Cotizacion, ItemCotizacion
from .facturacion import Factura, ItemFactura
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
    'AsientoContable', 'PlanContable', 'DetalleAsiento',
    # Ventas y Componentes
    'Venta', 'ItemVenta', 'AlojamientoReserva', 'TrasladoServicio', 'ActividadServicio', 'SegmentoVuelo',
    'FeeVenta', 'PagoVenta', 'AlquilerAutoReserva', 'EventoServicio', 'CircuitoTuristico', 'CircuitoDia',
    'PaqueteAereo', 'ServicioAdicionalDetalle', 'VentaParseMetadata', 'AuditLog',
    # Facturación
    'Factura', 'ItemFactura',
    # Boletos
    'BoletoImportado',
    'ComunicacionProveedor',
    # CMS
    'PaginaCMS', 'DestinoCMS', 'PaqueteTuristicoCMS', 'ArticuloBlog', 'Testimonio', 'MenuItemCMS', 'FormularioContactoCMS',
    # Catálogos
    'Pais', 'Ciudad', 'Moneda', 'TipoCambio', 'Proveedor', 'ProductoServicio',
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

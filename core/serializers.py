# Archivo: core/serializers.py
# Lazy loading facade for backward compatibility to avoid circular imports

import importlib

_SERIALIZER_MAPPINGS = {
    # apps.common.serializers
    "PaisSerializer": "apps.common.serializers",
    "CiudadSerializer": "apps.common.serializers",
    "AerolineaSerializer": "apps.common.serializers",
    "AuditLogSerializer": "apps.common.serializers",
    "UsuarioSerializer": "apps.common.serializers",
    "AgenciaSerializer": "apps.common.serializers",
    "UsuarioAgenciaSerializer": "apps.common.serializers",
    "CrearUsuarioAgenciaSerializer": "apps.common.serializers",
    "ComunicacionProveedorSerializer": "apps.common.serializers",
    # apps.finance.serializers
    "MonedaSerializer": "apps.finance.serializers",
    "ItemFacturaSerializer": "apps.finance.serializers",
    "FacturaSerializer": "apps.finance.serializers",
    # apps.crm.serializers
    "CoreClienteSerializer": "apps.crm.serializers",
    "PasaporteEscaneadoSerializer": "apps.crm.serializers",
    # apps.bookings.serializers
    "ProveedorSerializer": "apps.bookings.serializers",
    "ComisionProveedorServicioSerializer": "apps.bookings.serializers",
    "ProductoServicioSerializer": "apps.bookings.serializers",
    "BoletoImportadoSerializer": "apps.bookings.serializers",
    "ItemVentaSerializer": "apps.bookings.serializers",
    "SegmentoVueloSerializer": "apps.bookings.serializers",
    "AlojamientoReservaSerializer": "apps.bookings.serializers",
    "TrasladoServicioSerializer": "apps.bookings.serializers",
    "ActividadServicioSerializer": "apps.bookings.serializers",
    "AlquilerAutoReservaSerializer": "apps.bookings.serializers",
    "EventoServicioSerializer": "apps.bookings.serializers",
    "CircuitoDiaSerializer": "apps.bookings.serializers",
    "CircuitoTuristicoSerializer": "apps.bookings.serializers",
    "PaqueteAereoSerializer": "apps.bookings.serializers",
    "ServicioAdicionalDetalleSerializer": "apps.bookings.serializers",
    "FeeVentaSerializer": "apps.bookings.serializers",
    "PagoVentaSerializer": "apps.bookings.serializers",
    "VentaSerializer": "apps.bookings.serializers",
    "VentaParseMetadataSerializer": "apps.bookings.serializers",
    "ItinerarioSegmentoSerializer": "apps.bookings.serializers",
    "GeminiBoletoParseadoSerializer": "apps.bookings.serializers",
    # apps.contabilidad.serializers
    "DetalleAsientoSerializer": "apps.contabilidad.serializers",
    "AsientoContableSerializer": "apps.contabilidad.serializers",
}


def __getattr__(name):
    if name in _SERIALIZER_MAPPINGS:
        module_path = _SERIALIZER_MAPPINGS[name]
        module = importlib.import_module(module_path)
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")

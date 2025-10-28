# Views organizadas por dominio
from .auth_views import HealthCheckView, LoginView
from .venta_views import VentaViewSet, FeeVentaViewSet, PagoVentaViewSet, VentaParseMetadataViewSet
from .factura_views import FacturaViewSet
from .contabilidad_views import AsientoContableViewSet
from .catalogo_views import PaisViewSet, CiudadViewSet, MonedaViewSet, TipoCambioViewSet, ProveedorViewSet, ProductoServicioViewSet
from .boleto_views import BoletoImportadoViewSet, BoletoUploadAPIView
from .servicio_views import (
    SegmentoVueloViewSet, AlojamientoReservaViewSet, TrasladoServicioViewSet,
    ActividadServicioViewSet, AlquilerAutoReservaViewSet, EventoServicioViewSet,
    CircuitoTuristicoViewSet, CircuitoDiaViewSet, PaqueteAereoViewSet,
    ServicioAdicionalDetalleViewSet
)
from .cms_views import PaginaCMSDetailView, PaqueteCMSListView
from .dashboard_views import HomeView, dashboard_stats_api
from .audit_views import AuditLogViewSet

__all__ = [
    'HealthCheckView', 'LoginView',
    'VentaViewSet', 'FeeVentaViewSet', 'PagoVentaViewSet', 'VentaParseMetadataViewSet',
    'FacturaViewSet', 'AsientoContableViewSet',
    'PaisViewSet', 'CiudadViewSet', 'MonedaViewSet', 'TipoCambioViewSet',
    'ProveedorViewSet', 'ProductoServicioViewSet',
    'BoletoImportadoViewSet', 'BoletoUploadAPIView',
    'SegmentoVueloViewSet', 'AlojamientoReservaViewSet', 'TrasladoServicioViewSet',
    'ActividadServicioViewSet', 'AlquilerAutoReservaViewSet', 'EventoServicioViewSet',
    'CircuitoTuristicoViewSet', 'CircuitoDiaViewSet', 'PaqueteAereoViewSet',
    'ServicioAdicionalDetalleViewSet',
    'PaginaCMSDetailView', 'PaqueteCMSListView',
    'HomeView', 'dashboard_stats_api',
    'AuditLogViewSet',
]

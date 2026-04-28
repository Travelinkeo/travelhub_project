# Views package - Export ViewSets from views.py file
import sys
import os
import traceback

core_dir = os.path.dirname(os.path.dirname(__file__))
views_file = os.path.join(core_dir, 'views_legacy.py')

if os.path.exists(views_file):
    import importlib.util
    spec = importlib.util.spec_from_file_location("core.views_module", views_file)
    if spec and spec.loader:
        views_module = importlib.util.module_from_spec(spec)
        sys.modules['core.views_module'] = views_module
        try:
            spec.loader.exec_module(views_module)
            # Export all ViewSets
            ProveedorViewSet = getattr(views_module, 'ProveedorViewSet', None)
            VentaViewSet = getattr(views_module, 'VentaViewSet', None)
            FacturaViewSet = getattr(views_module, 'FacturaViewSet', None)
            AsientoContableViewSet = getattr(views_module, 'AsientoContableViewSet', None)
            SegmentoVueloViewSet = getattr(views_module, 'SegmentoVueloViewSet', None)
            AlojamientoReservaViewSet = getattr(views_module, 'AlojamientoReservaViewSet', None)
            TrasladoServicioViewSet = getattr(views_module, 'TrasladoServicioViewSet', None)
            ActividadServicioViewSet = getattr(views_module, 'ActividadServicioViewSet', None)
            FeeVentaViewSet = getattr(views_module, 'FeeVentaViewSet', None)
            PagoVentaViewSet = getattr(views_module, 'PagoVentaViewSet', None)
            VentaParseMetadataViewSet = getattr(views_module, 'VentaParseMetadataViewSet', None)
            AlquilerAutoReservaViewSet = getattr(views_module, 'AlquilerAutoReservaViewSet', None)
            EventoServicioViewSet = getattr(views_module, 'EventoServicioViewSet', None)
            CircuitoTuristicoViewSet = getattr(views_module, 'CircuitoTuristicoViewSet', None)
            CircuitoDiaViewSet = getattr(views_module, 'CircuitoDiaViewSet', None)
            PaqueteAereoViewSet = getattr(views_module, 'PaqueteAereoViewSet', None)
            ServicioAdicionalDetalleViewSet = getattr(views_module, 'ServicioAdicionalDetalleViewSet', None)
            BoletoImportadoViewSet = getattr(views_module, 'BoletoImportadoViewSet', None)
            BoletoImportadoListView = getattr(views_module, 'BoletoImportadoListView', None)
            BoletoManualEntryView = getattr(views_module, 'BoletoManualEntryView', None)
            upload_boleto_file = getattr(views_module, 'upload_boleto_file', None)
            delete_boleto_importado = getattr(views_module, 'delete_boleto_importado', None)
            SalesSummaryView = getattr(views_module, 'SalesSummaryView', None)
            AirTicketsEditableListView = getattr(views_module, 'AirTicketsEditableListView', None)
            AuditLogViewSet = getattr(views_module, 'AuditLogViewSet', None)
        except Exception as e:
            print(f"Warning: Could not load ViewSets from views.py: {e}")
            traceback.print_exc()

# Import specific views to expose them under core.views
from .boleto_views import BoletoUploadAPIView
from . import flights_views, catalogos_views, inventario_views
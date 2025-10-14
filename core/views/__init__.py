# Views package - Export ViewSets from views.py file
import sys
import os

core_dir = os.path.dirname(os.path.dirname(__file__))
views_file = os.path.join(core_dir, 'views.py')

if os.path.exists(views_file):
    import importlib.util
    spec = importlib.util.spec_from_file_location("core.views_module", views_file)
    if spec and spec.loader:
        views_module = importlib.util.module_from_spec(spec)
        sys.modules['core.views_module'] = views_module
        try:
            spec.loader.exec_module(views_module)
            # Export all ViewSets
            ProveedorViewSet = views_module.ProveedorViewSet
            VentaViewSet = views_module.VentaViewSet
            FacturaViewSet = views_module.FacturaViewSet
            AsientoContableViewSet = views_module.AsientoContableViewSet
            SegmentoVueloViewSet = views_module.SegmentoVueloViewSet
            AlojamientoReservaViewSet = views_module.AlojamientoReservaViewSet
            TrasladoServicioViewSet = views_module.TrasladoServicioViewSet
            ActividadServicioViewSet = views_module.ActividadServicioViewSet
            FeeVentaViewSet = views_module.FeeVentaViewSet
            PagoVentaViewSet = views_module.PagoVentaViewSet
            VentaParseMetadataViewSet = views_module.VentaParseMetadataViewSet
            AlquilerAutoReservaViewSet = views_module.AlquilerAutoReservaViewSet
            EventoServicioViewSet = views_module.EventoServicioViewSet
            CircuitoTuristicoViewSet = views_module.CircuitoTuristicoViewSet
            CircuitoDiaViewSet = views_module.CircuitoDiaViewSet
            PaqueteAereoViewSet = views_module.PaqueteAereoViewSet
            ServicioAdicionalDetalleViewSet = views_module.ServicioAdicionalDetalleViewSet
            BoletoImportadoViewSet = views_module.BoletoImportadoViewSet
            AuditLogViewSet = views_module.AuditLogViewSet
            dashboard_stats_api = views_module.dashboard_stats_api
        except Exception as e:
            print(f"Warning: Could not load ViewSets from views.py: {e}")
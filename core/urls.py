# Contenido del archivo core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VentaViewSet,
    FacturaViewSet,
    AsientoContableViewSet,
    SegmentoVueloViewSet,
    AlojamientoReservaViewSet,
    TrasladoServicioViewSet,
    ActividadServicioViewSet,
    FeeVentaViewSet,
    PagoVentaViewSet,
    HomeView,
    PaginaCMSDetailView,
    PaqueteCMSListView,
    BoletoImportadoListView,
    BoletoManualEntryView,
    SalesSummaryView,
    AirTicketsEditableListView,
)

router = DefaultRouter()
router.register(r'ventas', VentaViewSet, basename='venta')
router.register(r'facturas', FacturaViewSet, basename='factura')
router.register(r'asientoscontables', AsientoContableViewSet, basename='asientocontable')
router.register(r'segmentos-vuelo', SegmentoVueloViewSet, basename='segmento-vuelo')
router.register(r'alojamientos', AlojamientoReservaViewSet, basename='alojamiento-reserva')
router.register(r'traslados', TrasladoServicioViewSet, basename='traslado-servicio')
router.register(r'actividades', ActividadServicioViewSet, basename='actividad-servicio')
router.register(r'fees-venta', FeeVentaViewSet, basename='fee-venta')
router.register(r'pagos-venta', PagoVentaViewSet, basename='pago-venta')

from . import views

app_name = 'core'

urlpatterns = [
    path('api/', include(router.urls)),
    path('', HomeView.as_view(), name='home'),
    path('pagina/<slug:slug>/', PaginaCMSDetailView.as_view(), name='pagina_cms_detalle'),
    path('paquetes/', PaqueteCMSListView.as_view(), name='lista_paquetes_cms'),
    path('dashboard/boletos/', BoletoImportadoListView.as_view(), name='dashboard_boletos'),
    path('boletos/manual/entrada/', BoletoManualEntryView.as_view(), name='manual_ticket_entry'),
    path('boletos/upload/', views.upload_boleto_file, name='upload_boleto_file'),
    path('boletos/eliminar/<int:pk>/', views.delete_boleto_importado, name='delete_boleto_importado'),
    path('dashboard/ventas/resumen/', SalesSummaryView.as_view(), name='dashboard_resumen_ventas'),
    path('dashboard/ventas/boletos-aereos/', AirTicketsEditableListView.as_view(), name='air_tickets_editable'),
]

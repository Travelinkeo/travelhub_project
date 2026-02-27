from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    # Ventas
    path('ventas/', views.VentaListView.as_view(), name='venta_list'),
    path('ventas/nueva/', views.VentaCreateView.as_view(), name='venta_create'),
    path('ventas/<int:pk>/', views.VentaDetailView.as_view(), name='venta_detail'),
    path('ventas/<int:pk>/editar/', views.VentaUpdateView.as_view(), name='venta_update'),
    path('ventas/<int:pk>/eliminar/', views.VentaDeleteView.as_view(), name='venta_delete'),
    
    # HTMX Inline actions for Venta Detail
    path('ventas/<int:venta_pk>/items/agregar/', views.ItemVentaCreateView.as_view(), name='item_venta_add'),
    path('ventas/items/<int:pk>/editar/', views.ItemVentaUpdateView.as_view(), name='item_venta_edit'),
    path('ventas/<int:venta_pk>/fees/agregar/', views.FeeVentaCreateView.as_view(), name='fee_venta_add'),
    path('ventas/<int:venta_pk>/pagos/agregar/', views.PagoVentaCreateView.as_view(), name='pago_venta_add'),
]

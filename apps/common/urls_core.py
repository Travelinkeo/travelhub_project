from django.urls import path

from apps.common.views.catalogos_views import (
    AerolineaListView,
    CatalogosCenterView,
    ComisionProveedorServicioCreateView,
    ComisionProveedorServicioDeleteView,
    ComisionProveedorServicioListView,
    ComisionProveedorServicioUpdateView,
    GeografiaListView,
    ProductoServicioListView,
    SincronizarTasasActionView,
    TipoCambioCreateView,
    TipoCambioListView,
)
from apps.bookings.views import proveedores_views
from core.views import inventario_views


urlpatterns = [
    # Centro de Catálogos
    path('setup/catalogos/', CatalogosCenterView.as_view(), name='catalogos_center'),
    path('setup/catalogos/aerolineas/', AerolineaListView.as_view(), name='aerolineas_list'),
    path('setup/catalogos/productos/', ProductoServicioListView.as_view(), name='productos_list'),
    path('setup/catalogos/geografia/', GeografiaListView.as_view(), name='geografia_list'),
    
    # Catálogo Terrestre (Inventario Propio)
    path('inventario/terrestre/', inventario_views.CatalogoTerrestreListView.as_view(), name='catalogo_terrestre'),
    path('inventario/terrestre/nuevo/', inventario_views.ProductoTerrestreCreateView.as_view(), name='producto_terrestre_create'),
    
    # Proveedores (Catálogos)
    path('setup/catalogos/proveedores/', proveedores_views.ProveedorListView.as_view(), name='proveedores_list'),
    path('setup/catalogos/proveedores/nuevo/', proveedores_views.ProveedorCreateView.as_view(), name='proveedores_nuevo'),
    path('setup/catalogos/proveedores/nuevo/', proveedores_views.ProveedorCreateView.as_view(), name='proveedor_create'),
    path('setup/catalogos/proveedores/<int:pk>/editar/', proveedores_views.ProveedorUpdateView.as_view(), name='proveedores_editar'),
    path('setup/catalogos/proveedores/<int:pk>/editar/', proveedores_views.ProveedorUpdateView.as_view(), name='proveedor_update'),
    path('setup/catalogos/proveedores/<int:pk>/eliminar/', proveedores_views.ProveedorDeleteView.as_view(), name='proveedores_eliminar'),
    path('setup/catalogos/proveedores/<int:pk>/eliminar/', proveedores_views.ProveedorDeleteView.as_view(), name='proveedor_delete'),

    
    # ERP Proveedores Dashboard
    path('dashboard/erp/proveedores/', proveedores_views.ProveedorListView.as_view(), name='proveedores_list_erp'),
    path('dashboard/erp/proveedores/nuevo/', proveedores_views.ProveedorCreateView.as_view(), name='proveedor_create_erp'),
    path('dashboard/erp/proveedores/<int:pk>/editar/', proveedores_views.ProveedorUpdateView.as_view(), name='proveedor_update_erp'),
    
    # Comisiones
    path('setup/catalogos/comisiones/', ComisionProveedorServicioListView.as_view(), name='comisiones_list'),
    path('setup/catalogos/comisiones/nuevo/', ComisionProveedorServicioCreateView.as_view(), name='comisiones_nuevo'),
    path('setup/catalogos/comisiones/<int:pk>/editar/', ComisionProveedorServicioUpdateView.as_view(), name='comisiones_editar'),
    path('setup/catalogos/comisiones/<int:pk>/eliminar/', ComisionProveedorServicioDeleteView.as_view(), name='comisiones_eliminar'),
    
    # Tasas de Cambio
    path('setup/tasas/', TipoCambioListView.as_view(), name='tasas_list'),
    path('setup/tasas/nueva/', TipoCambioCreateView.as_view(), name='tasas_nuevo'),
    path('setup/tasas/sincronizar/', SincronizarTasasActionView.as_view(), name='tasas_sincronizar'),
]

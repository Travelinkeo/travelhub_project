from django.urls import path
from django.utils.module_loading import import_string

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

ProveedorListView = import_string("apps.bookings.views.proveedores_views.ProveedorListView")
ProveedorCreateView = import_string("apps.bookings.views.proveedores_views.ProveedorCreateView")
ProveedorUpdateView = import_string("apps.bookings.views.proveedores_views.ProveedorUpdateView")
ProveedorDeleteView = import_string("apps.bookings.views.proveedores_views.ProveedorDeleteView")

CatalogoTerrestreListView = import_string("core.views.inventario_views.CatalogoTerrestreListView")
ProductoTerrestreCreateView = import_string(
    "core.views.inventario_views.ProductoTerrestreCreateView"
)

urlpatterns = [
    # Centro de Catálogos
    path("setup/catalogos/", CatalogosCenterView.as_view(), name="catalogos_center"),
    path("setup/catalogos/aerolineas/", AerolineaListView.as_view(), name="aerolineas_list"),
    path("setup/catalogos/productos/", ProductoServicioListView.as_view(), name="productos_list"),
    path("setup/catalogos/geografia/", GeografiaListView.as_view(), name="geografia_list"),
    # Catálogo Terrestre (Inventario Propio)
    path(
        "inventario/terrestre/",
        CatalogoTerrestreListView.as_view(),
        name="catalogo_terrestre",
    ),
    path(
        "inventario/terrestre/nuevo/",
        ProductoTerrestreCreateView.as_view(),
        name="producto_terrestre_create",
    ),
    # Proveedores (Catálogos)
    path(
        "setup/catalogos/proveedores/",
        ProveedorListView.as_view(),
        name="proveedores_list",
    ),
    path(
        "setup/catalogos/proveedores/nuevo/",
        ProveedorCreateView.as_view(),
        name="proveedores_nuevo",
    ),
    path(
        "setup/catalogos/proveedores/nuevo/",
        ProveedorCreateView.as_view(),
        name="proveedor_create",
    ),
    path(
        "setup/catalogos/proveedores/<int:pk>/editar/",
        ProveedorUpdateView.as_view(),
        name="proveedores_editar",
    ),
    path(
        "setup/catalogos/proveedores/<int:pk>/editar/",
        ProveedorUpdateView.as_view(),
        name="proveedor_update",
    ),
    path(
        "setup/catalogos/proveedores/<int:pk>/eliminar/",
        ProveedorDeleteView.as_view(),
        name="proveedores_eliminar",
    ),
    path(
        "setup/catalogos/proveedores/<int:pk>/eliminar/",
        ProveedorDeleteView.as_view(),
        name="proveedor_delete",
    ),
    # ERP Proveedores Dashboard
    path(
        "dashboard/erp/proveedores/",
        ProveedorListView.as_view(),
        name="proveedores_list_erp",
    ),
    path(
        "dashboard/erp/proveedores/nuevo/",
        ProveedorCreateView.as_view(),
        name="proveedor_create_erp",
    ),
    path(
        "dashboard/erp/proveedores/<int:pk>/editar/",
        ProveedorUpdateView.as_view(),
        name="proveedor_update_erp",
    ),
    # Comisiones
    path(
        "setup/catalogos/comisiones/",
        ComisionProveedorServicioListView.as_view(),
        name="comisiones_list",
    ),
    path(
        "setup/catalogos/comisiones/nuevo/",
        ComisionProveedorServicioCreateView.as_view(),
        name="comisiones_nuevo",
    ),
    path(
        "setup/catalogos/comisiones/<int:pk>/editar/",
        ComisionProveedorServicioUpdateView.as_view(),
        name="comisiones_editar",
    ),
    path(
        "setup/catalogos/comisiones/<int:pk>/eliminar/",
        ComisionProveedorServicioDeleteView.as_view(),
        name="comisiones_eliminar",
    ),
    # Tasas de Cambio
    path("setup/tasas/", TipoCambioListView.as_view(), name="tasas_list"),
    path("setup/tasas/nueva/", TipoCambioCreateView.as_view(), name="tasas_nuevo"),
    path(
        "setup/tasas/sincronizar/", SincronizarTasasActionView.as_view(), name="tasas_sincronizar"
    ),
]

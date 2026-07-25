# apps/common/urls_admin.py
"""Configuración del panel de administración para common.
"""

from django.urls import path

from apps.common.views import catalogos_views

app_name = "common_admin"

urlpatterns = [
    # Aerolineas
    path("aerolineas/", catalogos_views.AerolineaListView.as_view(), name="aerolinea_list"),
    path(
        "aerolineas/nueva/", catalogos_views.AerolineaCreateView.as_view(), name="aerolinea_create"
    ),
    path(
        "aerolineas/<int:pk>/editar/",
        catalogos_views.AerolineaUpdateView.as_view(),
        name="aerolinea_update",
    ),
    path(
        "aerolineas/<int:pk>/eliminar/",
        catalogos_views.AerolineaDeleteView.as_view(),
        name="aerolinea_delete",
    ),
    # Geografia
    path("geografia/", catalogos_views.GeografiaListView.as_view(), name="geografia_list"),
    path("paises/nuevo/", catalogos_views.PaisCreateView.as_view(), name="pais_create"),
    path("paises/<int:pk>/editar/", catalogos_views.PaisUpdateView.as_view(), name="pais_update"),
    path("paises/<int:pk>/eliminar/", catalogos_views.PaisDeleteView.as_view(), name="pais_delete"),
    path("ciudades/nueva/", catalogos_views.CiudadCreateView.as_view(), name="ciudad_create"),
    path(
        "ciudades/<int:pk>/editar/",
        catalogos_views.CiudadUpdateView.as_view(),
        name="ciudad_update",
    ),
    path(
        "ciudades/<int:pk>/eliminar/",
        catalogos_views.CiudadDeleteView.as_view(),
        name="ciudad_delete",
    ),
]

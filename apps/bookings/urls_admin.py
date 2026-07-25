# apps/bookings/urls_admin.py
"""Configuración del panel de administración para bookings.
"""

from django.urls import path

from apps.bookings.views import admin_views

app_name = "bookings_admin"

urlpatterns = [
    # Productos y Servicios
    path(
        "productoservicio/",
        admin_views.ProductoServicioListView.as_view(),
        name="productoservicio_list",
    ),
    path(
        "productoservicio/nueva/",
        admin_views.ProductoServicioCreateView.as_view(),
        name="productoservicio_create",
    ),
    path(
        "productoservicio/<int:pk>/editar/",
        admin_views.ProductoServicioUpdateView.as_view(),
        name="productoservicio_update",
    ),
    path(
        "productoservicio/<int:pk>/eliminar/",
        admin_views.ProductoServicioDeleteView.as_view(),
        name="productoservicio_delete",
    ),
    # Cruceros
    path("cruceros/", admin_views.CruceroReservaListView.as_view(), name="cruceroreserva_list"),
    path(
        "cruceros/nueva/",
        admin_views.CruceroReservaCreateView.as_view(),
        name="cruceroreserva_create",
    ),
    path(
        "cruceros/<int:pk>/editar/",
        admin_views.CruceroReservaUpdateView.as_view(),
        name="cruceroreserva_update",
    ),
    path(
        "cruceros/<int:pk>/eliminar/",
        admin_views.CruceroReservaDeleteView.as_view(),
        name="cruceroreserva_delete",
    ),
]

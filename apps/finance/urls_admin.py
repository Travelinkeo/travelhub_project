# apps/finance/urls_admin.py
from django.urls import path

from apps.finance.views import admin_views

app_name = "finance_admin"

urlpatterns = [
    # Monedas y Tasas
    path("monedas/", admin_views.MonedaListView.as_view(), name="moneda_list"),
    path("monedas/nueva/", admin_views.MonedaCreateView.as_view(), name="moneda_create"),
    path("monedas/<int:pk>/editar/", admin_views.MonedaUpdateView.as_view(), name="moneda_update"),
    path(
        "monedas/<int:pk>/eliminar/", admin_views.MonedaDeleteView.as_view(), name="moneda_delete"
    ),
    path("tipocambio/nuevo/", admin_views.TipoCambioCreateView.as_view(), name="tipocambio_create"),
    path(
        "tipocambio/<int:pk>/editar/",
        admin_views.TipoCambioUpdateView.as_view(),
        name="tipocambio_update",
    ),
    path(
        "tipocambio/<int:pk>/eliminar/",
        admin_views.TipoCambioDeleteView.as_view(),
        name="tipocambio_delete",
    ),
    # Retenciones ISLR
    path(
        "retencionesislr/", admin_views.RetencionISLRListView.as_view(), name="retencionislr_list"
    ),
    path(
        "retencionesislr/nueva/",
        admin_views.RetencionISLRCreateView.as_view(),
        name="retencionislr_create",
    ),
    path(
        "retencionesislr/<int:pk>/editar/",
        admin_views.RetencionISLRUpdateView.as_view(),
        name="retencionislr_update",
    ),
    path(
        "retencionesislr/<int:pk>/eliminar/",
        admin_views.RetencionISLRDeleteView.as_view(),
        name="retencionislr_delete",
    ),
]

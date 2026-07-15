# apps/finance/urls_admin.py
from django.urls import path

from apps.finance.views import admin_views

app_name = "finance_admin"

urlpatterns = [
    # Monedas
    path("monedas/", admin_views.MonedaListView.as_view(), name="moneda_list"),
    path("monedas/nueva/", admin_views.MonedaCreateView.as_view(), name="moneda_create"),
    path("monedas/<int:pk>/editar/", admin_views.MonedaUpdateView.as_view(), name="moneda_update"),
    path(
        "monedas/<int:pk>/eliminar/", admin_views.MonedaDeleteView.as_view(), name="moneda_delete"
    ),
]

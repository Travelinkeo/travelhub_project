# core/urls_admin.py
from django.urls import path

from core.views import admin_views

app_name = "core_admin"

urlpatterns = [
    # Feature Flags
    path("featureflags/", admin_views.FeatureFlagListView.as_view(), name="featureflag_list"),
    path(
        "featureflags/nueva/",
        admin_views.FeatureFlagCreateView.as_view(),
        name="featureflag_create",
    ),
    path(
        "featureflags/<int:pk>/editar/",
        admin_views.FeatureFlagUpdateView.as_view(),
        name="featureflag_update",
    ),
    path(
        "featureflags/<int:pk>/eliminar/",
        admin_views.FeatureFlagDeleteView.as_view(),
        name="featureflag_delete",
    ),
    # Cron API Keys
    path("cronapikeys/", admin_views.CronApiKeyListView.as_view(), name="cronapikey_list"),
    path(
        "cronapikeys/nueva/", admin_views.CronApiKeyCreateView.as_view(), name="cronapikey_create"
    ),
    path(
        "cronapikeys/<int:pk>/editar/",
        admin_views.CronApiKeyUpdateView.as_view(),
        name="cronapikey_update",
    ),
    path(
        "cronapikeys/<int:pk>/eliminar/",
        admin_views.CronApiKeyDeleteView.as_view(),
        name="cronapikey_delete",
    ),
]

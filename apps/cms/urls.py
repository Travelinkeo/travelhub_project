from django.urls import path

from . import views
from .views.kb_views import (
    KBAdminListView,
    KBArticleCreateView,
    KBArticleDeleteView,
    KBArticleUpdateView,
    KBDetailView,
    KBHelpfulView,
    KBListView,
    KBSearchView,
)

app_name = "cms"

urlpatterns = [
    path("dashboard/", views.ContentDashboardView.as_view(), name="dashboard"),
    path("generate-article/", views.GenerateArticleView.as_view(), name="generate_article"),
    path(
        "generate-social-posts/<int:pk>/",
        views.GenerateSocialPostsView.as_view(),
        name="generate_social_posts",
    ),
    # Articulos
    path("articulo/nuevo/", views.ArticuloCreateView.as_view(), name="articulo_create"),
    path("articulo/<int:pk>/editar/", views.ArticuloUpdateView.as_view(), name="articulo_update"),
    path("articulo/<int:pk>/eliminar/", views.ArticuloDeleteView.as_view(), name="articulo_delete"),
    # Guias de Destino
    path("guia/nueva/", views.GuiaDestinoCreateView.as_view(), name="guia_create"),
    path("guia/<int:pk>/editar/", views.GuiaDestinoUpdateView.as_view(), name="guia_update"),
    path("guia/<int:pk>/eliminar/", views.GuiaDestinoDeleteView.as_view(), name="guia_delete"),
    # AI Sugerencias
    path("ai-suggest/", views.AIGenerateSuggestionView.as_view(), name="ai_suggest"),
    # Knowledge Base
    path("kb/", KBListView.as_view(), name="kb_list"),
    path("kb/buscar/", KBSearchView.as_view(), name="kb_search"),
    path("kb/<slug:slug>/", KBDetailView.as_view(), name="kb_detail"),
    path("kb/<slug:slug>/votar/", KBHelpfulView.as_view(), name="kb_helpful"),
    path("kb/admin/", KBAdminListView.as_view(), name="kb_admin_list"),
    path("kb/admin/crear/", KBArticleCreateView.as_view(), name="kb_article_create"),
    path("kb/admin/<int:pk>/editar/", KBArticleUpdateView.as_view(), name="kb_article_edit"),
    path("kb/admin/<int:pk>/eliminar/", KBArticleDeleteView.as_view(), name="kb_article_delete"),
]

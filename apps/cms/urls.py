from django.urls import path
from . import views

app_name = 'cms'

urlpatterns = [
    path('dashboard/', views.ContentDashboardView.as_view(), name='dashboard'),
    path('generate-article/', views.GenerateArticleView.as_view(), name='generate_article'),
    path('generate-social-posts/<int:pk>/', views.GenerateSocialPostsView.as_view(), name='generate_social_posts'),
    
    # Articulos
    path('articulo/nuevo/', views.ArticuloCreateView.as_view(), name='articulo_create'),
    path('articulo/<int:pk>/editar/', views.ArticuloUpdateView.as_view(), name='articulo_update'),
    path('articulo/<int:pk>/eliminar/', views.ArticuloDeleteView.as_view(), name='articulo_delete'),
    
    # Guias de Destino
    path('guia/nueva/', views.GuiaDestinoCreateView.as_view(), name='guia_create'),
    path('guia/<int:pk>/editar/', views.GuiaDestinoUpdateView.as_view(), name='guia_update'),
    path('guia/<int:pk>/eliminar/', views.GuiaDestinoDeleteView.as_view(), name='guia_delete'),
    # AI Sugerencias
    path('ai-suggest/', views.AIGenerateSuggestionView.as_view(), name='ai_suggest'),
]

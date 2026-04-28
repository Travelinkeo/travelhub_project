from django.urls import path
from . import views

app_name = 'marketing'

urlpatterns = [
    path('dashboard/', views.MarketingDashboardView.as_view(), name='dashboard'),
    path('generar-flyer/', views.GenerarFlyerView.as_view(), name='generar_flyer'),
    path('generar-copy/', views.GenerarCopyView.as_view(), name='generar_copy'),
    path('api/generate-social-advanced/', views.GenerarSocialMediaAdvancedView.as_view(), name='generar_social_advanced'),
    path('api/marketing-feed/', views.MarketingFeedView.as_view(), name='marketing_feed'),
    path('social-hub/', views.SocialHubView.as_view(), name='social_hub'),
    path('forecast/', views.AIForecastView.as_view(), name='forecast'),
]

from django.urls import path
from . import views

app_name = 'marketing'

urlpatterns = [
    path('dashboard/', views.MarketingDashboardView.as_view(), name='dashboard'),
    path('generar-flyer/', views.GenerarFlyerView.as_view(), name='generar_flyer'),
    path('generar-copy/', views.GenerarCopyView.as_view(), name='generar_copy'),
]

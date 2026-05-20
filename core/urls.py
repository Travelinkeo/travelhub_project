import logging
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import TokenObtainPairView

# Importaciones mínimas para rutas core
from core.views.onboarding_views import OnboardingAgencyView, SaaSOnboardingView
from core.views.auth_views import TokenLogoutView, MagicLinkRequestView, MagicLinkVerifyView
from django.contrib.auth import views as auth_views

logger = logging.getLogger(__name__)
app_name = 'core'

urlpatterns = [
    # --- ADMINISTRACIÓN Y AUTENTICACIÓN ---
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('api/auth/jwt/obtain/', TokenObtainPairView.as_view(), name='jwt_obtain_pair'),
    path('api/auth/jwt/logout/', TokenLogoutView.as_view(), name='jwt_logout'),

    # Magic Links
    path('auth/magic-request/', MagicLinkRequestView.as_view(), name='magic_link_request'),
    path('auth/magic/<str:token>/', MagicLinkVerifyView.as_view(), name='magic_link_verify'),
    
    # --- ONBOARDING (SaaS) ---
    path('onboarding/', SaaSOnboardingView.as_view(), name='onboarding_start'),
    path('onboarding/agency/', OnboardingAgencyView.as_view(), name='onboarding_agency'),

    # --- DASHBOARD PRINCIPAL ---
    # Redirige a la vista modern_dashboard que ahora reside en bookings
    path('', RedirectView.as_view(pattern_name='bookings:modern_dashboard', permanent=False), name='home'),
    path('dashboard/', RedirectView.as_view(pattern_name='bookings:modern_dashboard', permanent=False), name='dashboard_root'),
]

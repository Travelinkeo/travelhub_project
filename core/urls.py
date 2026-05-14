import logging
import json
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.generic import RedirectView, TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

# Importaciones mínimas para rutas core
from core.views.onboarding_views import OnboardingAgencyView, SaaSOnboardingView
from core.views.public_views import PublicHotelVoucherPDFView, PublicItineraryView, PublicVoucherPDFView
from core.views.health_views import health_check as health_check_view
from core.middleware import csp_report_view
from core.views.user_profile_views import TokenLogoutView
from apps.bookings.views.dashboard_views import DashboardView

logger = logging.getLogger(__name__)

app_name = 'core'

urlpatterns = [
    # --- ADMINISTRACIÓN Y AUTENTICACIÓN ---
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api/auth/jwt/obtain/', TokenObtainPairView.as_view(), name='jwt_obtain_pair'),
    path('api/auth/jwt/logout/', TokenLogoutView.as_view(), name='jwt_logout'),
    
    # --- ONBOARDING (SaaS) ---
    path('onboarding/', SaaSOnboardingView.as_view(), name='onboarding_start'),
    path('onboarding/agency/', OnboardingAgencyView.as_view(), name='onboarding_agency'),

    # --- DASHBOARD PRINCIPAL ---
    path('', RedirectView.as_view(pattern_name='core:modern_dashboard', permanent=False), name='home'),
    path('dashboard/', RedirectView.as_view(pattern_name='core:modern_dashboard', permanent=False), name='dashboard_root'),
    path('dashboard/modern/', DashboardView.as_view(), name='modern_dashboard'),

    # --- MÓDULOS MODULARIZADOS (INCLUDES) ---
    # Nota: Mantenemos la estructura de prefijos para evitar colisiones y organizar el código
    path('finance/', include('apps.finance.urls')),
    path('bookings/', include('apps.bookings.urls')),
    path('crm/', include('apps.crm.urls')),
    path('system/', include('core.urls_system')),
    
    # --- API GLOBAL (Para compatibilidad con el Frontend) ---
    # Incluimos los routers de cada app bajo el prefijo api/ para no romper llamadas AJAX
    path('api/', include('apps.finance.urls')), # Finance tiene un path('', include(router.urls))
    path('api/', include('apps.bookings.urls')),
    path('api/', include('apps.crm.urls')),
    path('api/', include('core.urls_system')),

    # Redirecciones Legacy para no romper el sistema (Compatibilidad)
    path('dashboard/erp/ventas/', RedirectView.as_view(pattern_name='bookings:venta_list', permanent=True), name='ventas_dashboard'),
    path('dashboard/erp/clientes/', RedirectView.as_view(pattern_name='crm:cliente_list', permanent=True), name='clientes_list'),
    path('dashboard/erp/pasajeros/', RedirectView.as_view(pattern_name='crm:pasajero_list', permanent=True), name='pasajeros_list'),

    # --- VISTAS PÚBLICAS (White-Label) ---
    path('v/<uuid:token>/', PublicItineraryView.as_view(), name='public_itinerary'),
    path('v/<uuid:token>/pdf/', PublicVoucherPDFView.as_view(), name='public_voucher_pdf'),
    path('v/hotel/<int:alojamiento_id>/pdf/', PublicHotelVoucherPDFView.as_view(), name='public_hotel_voucher'),

    # --- INFRAESTRUCTURA Y SALUD ---
    path('health/', health_check_view, name='health_check'),
    path('csp-report/', csp_report_view, name='csp_report'),
    
    # --- DOCUMENTACIÓN API ---
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

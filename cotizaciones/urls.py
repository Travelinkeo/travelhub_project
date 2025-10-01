from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CotizacionViewSet, ItemCotizacionViewSet

router = DefaultRouter()
router.register(r'cotizaciones', CotizacionViewSet)
router.register(r'items-cotizacion', ItemCotizacionViewSet)

app_name = 'cotizaciones'

urlpatterns = [
    path('api/', include(router.urls)),
]
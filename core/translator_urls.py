# Archivo: core/translator_urls.py

from django.urls import path
from .views.translator_views import (
    translate_itinerary_api,
    calculate_ticket_price_api,
    get_supported_gds_api,
    get_airlines_catalog_api,
    get_airports_catalog_api,
    validate_itinerary_format_api,
    batch_translate_api
)

app_name = 'translator'

urlpatterns = [
    # Traducción de itinerarios
    path('itinerary/', translate_itinerary_api, name='translate_itinerary'),
    
    # Cálculo de precios
    path('calculate/', calculate_ticket_price_api, name='calculate_price'),
    
    # Catálogos y información
    path('gds/', get_supported_gds_api, name='supported_gds'),
    path('airlines/', get_airlines_catalog_api, name='airlines_catalog'),
    path('airports/', get_airports_catalog_api, name='airports_catalog'),
    
    # Validación
    path('validate/', validate_itinerary_format_api, name='validate_format'),
    
    # Procesamiento en lote
    path('batch/', batch_translate_api, name='batch_translate'),
]
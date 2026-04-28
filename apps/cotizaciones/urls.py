from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CotizacionViewSet, 
    ItemCotizacionViewSet, 
    MagicQuoterView, 
    MagicQuoterAIView, 
    MagicQuoterSaveView,
    PublicQuoteDetailView
)
from .views_whatsapp import IncomingWhatsAppWebhook

router = DefaultRouter()
router.register(r'cotizaciones', CotizacionViewSet)
router.register(r'items-cotizacion', ItemCotizacionViewSet)

app_name = 'cotizaciones'

urlpatterns = [
    path('api/', include(router.urls)),
    path('whatsapp/webhook/', IncomingWhatsAppWebhook.as_view(), name='whatsapp-webhook'),
    
    # --- MAGIC QUOTER ---
    path('magic/', MagicQuoterView.as_view(), name='magic_quoter'),
    path('magic/ai/', MagicQuoterAIView.as_view(), name='magic_quoter_ai'),
    path('magic/save/', MagicQuoterSaveView.as_view(), name='magic_quoter_save'),
    path('public/<uuid:quote_uuid>/', PublicQuoteDetailView.as_view(), name='public_quote'),
]
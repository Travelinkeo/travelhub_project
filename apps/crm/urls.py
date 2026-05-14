from django.urls import path

from .views import (
    clientes_views, pasajeros_views, ocr_views, actions_views,
    freelancer_views, kanban_views, webhook_views
)
from .views.ai_chat_views import GenerateSuggestedReplyView

from .views.inbox_views import ChatThreadView, InboxView, SendMessageView
from .views.marketing_views import AnalyzeCampaignPromptView, DispatchCampaignView, MarketingHubView
from core.views.search_views import ClienteSearchAPIView
from core.views.id_scanner_views import CedulaScannerAPIView
from core.views.ocr_views import OCRPassportView

# API ViewSets
from rest_framework.routers import DefaultRouter
from apps.crm.api import ClienteViewSet, PasajeroViewSet



app_name = 'crm'

router = DefaultRouter()
router.register(r'clientes', ClienteViewSet, basename='cliente')
router.register(r'pasajeros', PasajeroViewSet, basename='pasajero')


urlpatterns = [
    # Clientes
    path('clientes/', clientes_views.ClienteListView.as_view(), name='cliente_list'),
    path('clientes/nuevo/', clientes_views.ClienteCreateView.as_view(), name='cliente_create'),
    path('clientes/<int:pk>/', clientes_views.ClienteDetailView.as_view(), name='cliente_detail'),
    path('clientes/<int:pk>/editar/', clientes_views.ClienteUpdateView.as_view(), name='cliente_update'),
    path('clientes/<int:pk>/eliminar/', clientes_views.ClienteDeleteView.as_view(), name='cliente_delete'),
    
    # Pasajeros
    path('pasajeros/', pasajeros_views.PasajeroListView.as_view(), name='pasajero_list'),
    path('pasajeros/nuevo/', pasajeros_views.PasajeroCreateView.as_view(), name='pasajero_create'),
    path('pasajeros/ocr/procesar/', ocr_views.PasajeroOCRProcessView.as_view(), name='pasajero_ocr_procesar'),
    path('pasajeros/ocr/guardar/', ocr_views.PasajeroOCRSaveView.as_view(), name='pasajero_ocr_guardar'),
    path('pasajeros/<int:pk>/', pasajeros_views.PasajeroDetailView.as_view(), name='pasajero_detail'),
    path('pasajeros/<int:pk>/editar/', pasajeros_views.PasajeroUpdateView.as_view(), name='pasajero_update'),
    path('pasajeros/<int:pk>/eliminar/', pasajeros_views.PasajeroDeleteView.as_view(), name='pasajero_delete'),
    path('pasajeros/<int:pk>/convertir/', actions_views.PasajeroConvertToClienteView.as_view(), name='pasajero_convert'),

    # Acciones
    path('pasajeros/search/', actions_views.PasajeroSearchView.as_view(), name='pasajero_search'),
    path('clientes/<int:pk>/vincular-pasajero/', actions_views.VincularPasajeroActionView.as_view(), name='vincular_pasajero'),

    
    # Webhooks & Bots
    path('webhook/whatsapp/', webhook_views.WhatsAppWebhookView.as_view(), name='whatsapp_webhook'),

    # Kanban CRM
    path('kanban/', kanban_views.KanbanBoardView.as_view(), name='kanban_board'),
    path('kanban/update/', kanban_views.UpdateLeadStageView.as_view(), name='kanban_update_stage'),

    # Portal Freelancer
    path('portal-agente/', freelancer_views.FreelancerDashboardView.as_view(), name='portal_freelancer'),

    # --- MOTOR DE MARKETING IA ---
    path('marketing/', MarketingHubView.as_view(), name='marketing_hub'),
    path('marketing/analyze/', AnalyzeCampaignPromptView.as_view(), name='analyze_campaign'),
    path('marketing/dispatch/', DispatchCampaignView.as_view(), name='dispatch_campaign'),

    # --- INBOX OMNICANAL (WA + CRM + IA) ---
    path('inbox/', InboxView.as_view(), name='inbox'),
    path('inbox/chat/<int:cliente_id>/', ChatThreadView.as_view(), name='chat_thread'),
    path('inbox/send/<int:cliente_id>/', SendMessageView.as_view(), name='send_message'),
    path('inbox/ai-reply/<int:cliente_id>/', GenerateSuggestedReplyView.as_view(), name='ai_suggested_reply'),

    # Búsqueda & Herramientas (Movido de core/urls.py)
    path('api/search/clientes/', ClienteSearchAPIView.as_view(), name='api_search_clientes'),
    path('api/crm/cedula-scanner/', CedulaScannerAPIView.as_view(), name='api_cedula_scanner'),
    path('api/ocr/passport/', OCRPassportView.as_view(), name='ocr_passport'),
    path('api/ocr/scan-id/', OCRPassportView.as_view(), name='api_scan_id'),

    # API
    path('api/', include(router.urls)),
]



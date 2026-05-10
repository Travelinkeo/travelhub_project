from django.urls import path
from . import views
from .views import webhook_views, kanban_views, freelancer_views
from .views.marketing_views import MarketingHubView, AnalyzeCampaignPromptView, DispatchCampaignView
from .views.inbox_views import InboxView, ChatThreadView, SendMessageView
from .views.ai_chat_views import GenerateSuggestedReplyView

app_name = 'crm'

urlpatterns = [
    # Clientes
    path('clientes/', views.ClienteListView.as_view(), name='cliente_list'),
    path('clientes/nuevo/', views.ClienteCreateView.as_view(), name='cliente_create'),
    path('clientes/<int:pk>/', views.ClienteDetailView.as_view(), name='cliente_detail'),
    path('clientes/<int:pk>/editar/', views.ClienteUpdateView.as_view(), name='cliente_update'),
    path('clientes/<int:pk>/eliminar/', views.ClienteDeleteView.as_view(), name='cliente_delete'),
    
    # Pasajeros
    path('pasajeros/', views.PasajeroListView.as_view(), name='pasajero_list'),
    path('pasajeros/nuevo/', views.PasajeroCreateView.as_view(), name='pasajero_create'),
    path('pasajeros/ocr/procesar/', views.PasajeroOCRProcessView.as_view(), name='pasajero_ocr_procesar'),
    path('pasajeros/ocr/guardar/', views.PasajeroOCRSaveView.as_view(), name='pasajero_ocr_guardar'),
    path('pasajeros/<int:pk>/', views.PasajeroDetailView.as_view(), name='pasajero_detail'),
    path('pasajeros/<int:pk>/editar/', views.PasajeroUpdateView.as_view(), name='pasajero_update'),
    path('pasajeros/<int:pk>/eliminar/', views.PasajeroDeleteView.as_view(), name='pasajero_delete'),
    path('pasajeros/<int:pk>/convertir/', views.PasajeroConvertToClienteView.as_view(), name='pasajero_convert'),

    # Acciones
    path('pasajeros/search/', views.PasajeroSearchView.as_view(), name='pasajero_search'),
    path('clientes/<int:pk>/vincular-pasajero/', views.VincularPasajeroActionView.as_view(), name='vincular_pasajero'),
    
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
]

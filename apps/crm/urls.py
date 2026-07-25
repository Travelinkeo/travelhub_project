"""Configuración de rutas (URLs) para la aplicación crm.
"""

from django.urls import include, path
from django.utils.module_loading import import_string
from django.views.generic import RedirectView

# API ViewSets
from rest_framework.routers import DefaultRouter

from apps.crm.api import ClienteViewSet, PasajeroViewSet

from .views import (
    actions_views,
    clientes_views,
    freelancer_views,
    import_views,
    kanban_views,
    ocr_views,
    pasajeros_views,
    webhook_views,
)
from .views.ai_chat_views import GenerateSuggestedReplyView
from .views.inbox_views import ChatThreadView, InboxSearchView, InboxView, SendMessageView
from .views.marketing_views import AnalyzeCampaignPromptView, DispatchCampaignView, MarketingHubView

app_name = "crm"


def dynamic_view(view_path):
    # dynamic_view: Dynamic view. Args: según implementación. Returns: según implementación.
    def lazy_view_handler(request, *args, **kwargs):
        # lazy_view_handler: Lazy view handler. Args: según implementación. Returns: según implementación.
        view_class = import_string(view_path)
        return view_class.as_view()(request, *args, **kwargs)

    return lazy_view_handler


router = DefaultRouter()
router.register(r"clientes", ClienteViewSet, basename="cliente")

router.register(r"pasajeros", PasajeroViewSet, basename="pasajero")

urlpatterns = [
    # Redirecciones Legacy
    path(
        "dashboard/erp/clientes/",
        RedirectView.as_view(pattern_name="crm:cliente_list", permanent=True),
        name="clientes_list",
    ),
    path(
        "dashboard/erp/pasajeros/",
        RedirectView.as_view(pattern_name="crm:pasajero_list", permanent=True),
        name="pasajeros_list",
    ),
    # Clientes
    path("clientes/", clientes_views.ClienteListView.as_view(), name="cliente_list"),
    path("clientes/nuevo/", clientes_views.ClienteCreateView.as_view(), name="cliente_create"),
    path("clientes/<int:pk>/", clientes_views.ClienteDetailView.as_view(), name="cliente_detail"),
    path(
        "clientes/<int:pk>/editar/",
        clientes_views.ClienteUpdateView.as_view(),
        name="cliente_update",
    ),
    path(
        "clientes/<int:pk>/eliminar/",
        clientes_views.ClienteDeleteView.as_view(),
        name="cliente_delete",
    ),
    # Pasajeros
    path("pasajeros/", pasajeros_views.PasajeroListView.as_view(), name="pasajero_list"),
    path("pasajeros/nuevo/", pasajeros_views.PasajeroCreateView.as_view(), name="pasajero_create"),
    path(
        "pasajeros/ocr/procesar/",
        ocr_views.PasajeroOCRProcessView.as_view(),
        name="pasajero_ocr_procesar",
    ),
    path(
        "pasajeros/ocr/guardar/",
        ocr_views.PasajeroOCRSaveView.as_view(),
        name="pasajero_ocr_guardar",
    ),
    path(
        "pasajeros/<int:pk>/", pasajeros_views.PasajeroDetailView.as_view(), name="pasajero_detail"
    ),
    path(
        "pasajeros/<int:pk>/editar/",
        pasajeros_views.PasajeroUpdateView.as_view(),
        name="pasajero_update",
    ),
    path(
        "pasajeros/<int:pk>/eliminar/",
        pasajeros_views.PasajeroDeleteView.as_view(),
        name="pasajero_delete",
    ),
    path(
        "pasajeros/<int:pk>/convertir/",
        actions_views.PasajeroConvertToClienteView.as_view(),
        name="pasajero_convert",
    ),
    # Acciones
    path("pasajeros/search/", actions_views.PasajeroSearchView.as_view(), name="pasajero_search"),
    path(
        "clientes/<int:pk>/vincular-pasajero/",
        actions_views.VincularPasajeroActionView.as_view(),
        name="vincular_pasajero",
    ),
    # Webhooks & Bots
    path("webhook/whatsapp/", webhook_views.WhatsAppWebhookView.as_view(), name="whatsapp_webhook"),
    path(
        "webhook/evolution/", webhook_views.EvolutionWebhookView.as_view(), name="evolution_webhook"
    ),
    # Kanban CRM
    path("kanban/", kanban_views.KanbanBoardView.as_view(), name="kanban_board"),
    path("kanban/update/", kanban_views.UpdateLeadStageView.as_view(), name="kanban_update_stage"),
    # Portal Freelancer
    path(
        "portal-agente/",
        freelancer_views.FreelancerDashboardView.as_view(),
        name="portal_freelancer",
    ),
    # --- MOTOR DE MARKETING IA ---
    path("marketing/", MarketingHubView.as_view(), name="marketing_hub"),
    path("marketing/analyze/", AnalyzeCampaignPromptView.as_view(), name="analyze_campaign"),
    path("marketing/dispatch/", DispatchCampaignView.as_view(), name="dispatch_campaign"),
    # --- INBOX OMNICANAL (WA + CRM + IA) ---
    path("inbox/", InboxView.as_view(), name="inbox"),
    path("inbox/search/", InboxSearchView.as_view(), name="inbox_search"),
    path("inbox/chat/<int:cliente_id>/", ChatThreadView.as_view(), name="chat_thread"),
    path("inbox/send/<int:cliente_id>/", SendMessageView.as_view(), name="send_message"),
    path(
        "inbox/ai-reply/<int:cliente_id>/",
        GenerateSuggestedReplyView.as_view(),
        name="ai_suggested_reply",
    ),
    # Búsqueda & Herramientas (Movido de core/urls.py)
    path(
        "api/search/clientes/",
        dynamic_view("core.views.search_views.ClienteSearchAPIView"),
        name="api_search_clientes",
    ),
    path(
        "api/crm/cedula-scanner/",
        dynamic_view("core.views.id_scanner_views.CedulaScannerAPIView"),
        name="api_cedula_scanner",
    ),
    path(
        "api/ocr/passport/",
        dynamic_view("core.views.ocr_views.OCRPassportView"),
        name="ocr_passport",
    ),
    path(
        "api/ocr/scan-id/", dynamic_view("core.views.ocr_views.OCRPassportView"), name="api_scan_id"
    ),
    # Importación Excel
    path(
        "clientes/importar/",
        import_views.ImportarClientesView.as_view(),
        name="importar_clientes",
    ),
    path(
        "clientes/importar/mapeo/",
        import_views.MapeoColumnasView.as_view(),
        name="importar_clientes_mapeo",
    ),
    path(
        "clientes/importar/progreso/<str:task_id>/",
        import_views.ImportarClientesProgressView.as_view(),
        name="importar_clientes_progreso",
    ),
    # API
    path("api/", include(router.urls)),
]

import json
import logging
from django.views.generic import ListView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.db.models import Max
from apps.crm.models import Cliente, MensajeWhatsApp
from core.services.whatsapp_service import enviar_mensaje_meta_api

logger = logging.getLogger(__name__)

class InboxView(LoginRequiredMixin, TemplateView):
    """
    Vista principal del Inbox Omnicanal.
    """
    template_name = "crm/inbox/omnichannel_inbox.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtenemos clientes que tienen mensajes de WhatsApp, ordenados por el más reciente
        clientes_activos = Cliente.objects.annotate(
            ultimo_mensaje_at=Max('mensajes_whatsapp__timestamp')
        ).filter(ultimo_mensaje_at__isnull=False).order_by('-ultimo_mensaje_at')
        
        context['clientes_activos'] = clientes_activos
        return context

class ChatThreadView(LoginRequiredMixin, View):
    """
    Endpoint HTMX para cargar el workspace de un cliente.
    """
    def get(self, request, cliente_id, *args, **kwargs):
        cliente = get_object_or_404(Cliente, pk=cliente_id)
        mensajes = cliente.mensajes_whatsapp.all().order_by('timestamp')
        
        # Obtener Lead activo (si existe) para el Sidebar derecho
        from apps.crm.models import OportunidadViaje

        lead = OportunidadViaje.objects.filter(cliente=cliente).exclude(etapa='LOS').first()
        
        return render(request, "crm/inbox/partials/chat_workspace.html", {
            'cliente': cliente,
            'mensajes': mensajes,
            'lead': lead
        })

class SendMessageView(LoginRequiredMixin, View):
    """
    Endpoint HTMX para enviar un mensaje manual.
    """
    def post(self, request, cliente_id, *args, **kwargs):
        cliente = get_object_or_404(Cliente, pk=cliente_id)
        texto = request.POST.get('texto') # Nombre del campo en el HTML
        
        if not texto:
            return HttpResponse(status=400)

        # 1. Enviar vía API de WhatsApp (Meta)
        try:
            exito = enviar_mensaje_meta_api(cliente.telefono_principal, texto)
            if not exito:
                logger.warning(f"Falla de envío Meta API para {cliente.id_cliente}")
        except Exception as e:
            logger.error(f"Error SendMessageView Meta: {e}")

        # 2. Guardar en Historial (OUT, es_bot=False)
        msg = MensajeWhatsApp.objects.create(
            cliente=cliente,
            direccion='OUT',
            texto=texto,
            es_bot=False,
            agencia=cliente.agencia
        )

        # 3. Devolver únicamente la nueva burbuja
        return render(request, "crm/inbox/partials/message_bubble.html", {
            'msg': msg
        })

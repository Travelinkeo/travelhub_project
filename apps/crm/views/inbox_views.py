import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import TemplateView, View

from apps.crm.models import Cliente, MensajeWhatsApp

logger = logging.getLogger(__name__)


class InboxView(LoginRequiredMixin, TemplateView):
    """
    Vista principal del Inbox Omnicanal.
    """

    template_name = "crm/inbox/omnichannel_inbox.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Clientes con mensajes, ordenados por el más reciente
        clientes_con_mensajes = (
            Cliente.objects.annotate(ultimo_mensaje_at=Max("mensajes_whatsapp__timestamp"))
            .filter(ultimo_mensaje_at__isnull=False)
            .order_by("-ultimo_mensaje_at")
        )
        # Clientes con teléfono pero sin mensajes (para iniciar conversaciones)
        clientes_sin_mensajes = (
            Cliente.objects.filter(
                mensajes_whatsapp__isnull=True,
                telefono_principal__isnull=False,
            )
            .exclude(telefono_principal__exact="")
            .order_by("nombres")
        )
        context["clientes_activos"] = list(clientes_con_mensajes) + list(clientes_sin_mensajes)
        # Si viene ?chat=ID, pre-seleccionar ese cliente
        chat_id = self.request.GET.get("chat")
        if chat_id:
            try:
                context["chat_id"] = int(chat_id)
            except (ValueError, TypeError):
                pass
        return context


class ChatThreadView(LoginRequiredMixin, View):
    """
    Endpoint HTMX para cargar el workspace de un cliente.
    """

    def get(self, request, cliente_id, *args, **kwargs):
        cliente = get_object_or_404(Cliente, pk=cliente_id)
        mensajes = cliente.mensajes_whatsapp.all().order_by("timestamp")

        # Obtener Lead activo (si existe) para el Sidebar derecho
        from apps.crm.models import OportunidadViaje

        lead = OportunidadViaje.objects.filter(cliente=cliente).exclude(etapa="LOS").first()

        return render(
            request,
            "crm/inbox/partials/chat_workspace.html",
            {"cliente": cliente, "mensajes": mensajes, "lead": lead},
        )


class InboxSearchView(LoginRequiredMixin, View):
    """
    Endpoint HTMX para buscar clientes en el inbox.
    """

    def get(self, request, *args, **kwargs):
        q = request.GET.get("q", "").strip()
        if not q:
            # Sin búsqueda, devolver la lista completa (como InboxView)
            clientes_con_mensajes = (
                Cliente.objects.annotate(ultimo_mensaje_at=Max("mensajes_whatsapp__timestamp"))
                .filter(ultimo_mensaje_at__isnull=False)
                .order_by("-ultimo_mensaje_at")
            )
            clientes_sin_mensajes = (
                Cliente.objects.filter(
                    mensajes_whatsapp__isnull=True,
                    telefono_principal__isnull=False,
                )
                .exclude(telefono_principal__exact="")
                .order_by("nombres")
            )
            clientes = list(clientes_con_mensajes) + list(clientes_sin_mensajes)
        else:
            clientes = (
                Cliente.objects.filter(
                    Q(nombres__icontains=q)
                    | Q(apellidos__icontains=q)
                    | Q(telefono_principal__icontains=q)
                    | Q(email__icontains=q),
                    telefono_principal__isnull=False,
                )
                .exclude(telefono_principal__exact="")
                .order_by("nombres")[:20]
            )
        return render(request, "crm/inbox/partials/client_list.html", {"clientes": clientes})


class SendMessageView(LoginRequiredMixin, View):
    """
    Endpoint HTMX para enviar un mensaje manual.
    """

    def post(self, request, cliente_id, *args, **kwargs):
        cliente = get_object_or_404(Cliente, pk=cliente_id)
        texto = request.POST.get("texto")

        if not texto:
            return HttpResponse(status=400)

        # 1. Enviar vía Celery task (Evolution API)
        try:
            from apps.common.tasks.evolution import send_evolution_message_task

            send_evolution_message_task.delay(
                agencia_id=cliente.agencia_id,
                phone_number=cliente.telefono_principal,
                text=texto,
            )
        except Exception as e:
            logger.error(f"Error encolando WhatsApp en inbox_views: {e}")

        # 2. Guardar en Historial (OUT, es_bot=False)
        msg = MensajeWhatsApp.objects.create(
            cliente=cliente, direccion="OUT", texto=texto, es_bot=False, agencia=cliente.agencia
        )

        # 3. Devolver únicamente la nueva burbuja
        return render(request, "crm/inbox/partials/message_bubble.html", {"msg": msg})

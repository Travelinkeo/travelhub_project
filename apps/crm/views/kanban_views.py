"""Vistas (views) de la aplicación crm.
"""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

# Importamos el modelo que creaste anteriormente
from apps.crm.models import OportunidadViaje
from core.api import get_user_active_agency

logger = logging.getLogger(__name__)


class KanbanBoardView(LoginRequiredMixin, View):
    """
    Renderiza el tablero principal de ventas, agrupando los leads por etapa.
    SaaSMixin no aplica aquí porque View no tiene get_queryset() — se implementa
    la lógica de filtrado por agencia directamente.
    """

    template_name = "crm/kanban_board.html"

    def get_queryset(self):
        """Retorna el queryset de OportunidadViaje filtrado por agencia del usuario."""
        user = self.request.user
        qs = OportunidadViaje.objects.all()
        if user.is_superuser:
            return qs
        agencia = get_user_active_agency(user)
        if agencia:
            return qs.filter(agencia=agencia)
        return qs.none()

    def get(self, request, *args, **kwargs):
        # Obtenemos todos los leads en UNA sola consulta, agrupando en Python
        # (evita 4 queries + 4 COUNT queries en el template)
        all_leads = list(
            self.get_queryset().select_related("cliente").order_by("etapa", "-creado_en")
        )

        leads_new = [lead for lead in all_leads if lead.etapa == "NEW"]
        leads_quo = [lead for lead in all_leads if lead.etapa == "QUO"]
        leads_pay = [lead for lead in all_leads if lead.etapa == "PAY"]
        leads_won = [lead for lead in all_leads if lead.etapa == "WON"]
        leads_los = [lead for lead in all_leads if lead.etapa == "LOS"]

        context = {
            "leads_new": leads_new,
            "leads_quo": leads_quo,
            "leads_pay": leads_pay,
            "leads_won": leads_won,
            "leads_los": leads_los,
            "leads_new_count": len(leads_new),
            "leads_quo_count": len(leads_quo),
            "leads_pay_count": len(leads_pay),
            "leads_won_count": len(leads_won),
            "leads_los_count": len(leads_los),
        }
        return render(request, self.template_name, context)


class UpdateLeadStageView(LoginRequiredMixin, View):
    """
    Endpoint reactivo (HTMX). Recibe el ID del Lead y su nueva etapa
    cuando el usuario suelta la tarjeta (Drop).
    """

    def post(self, request, *args, **kwargs):
        # post: Post. Args: según implementación. Returns: según implementación.
        lead_id = request.POST.get("lead_id")
        new_stage = request.POST.get("new_stage")

        if lead_id and new_stage:
            try:
                from core.api import get_agencia_or_403, get_object_tenant_or_404

                agencia = get_agencia_or_403(request)
                lead = get_object_tenant_or_404(OportunidadViaje, agencia, id=lead_id)

                # Validar que new_stage esté en las choices del modelo
                if new_stage in dict(OportunidadViaje.Etapa.choices):
                    lead.etapa = new_stage
                    lead.save()
                    logger.info(f"🃏 Lead {lead_id} movido a la etapa {new_stage}")

                    # HTMX no necesita renderizar nada de vuelta porque
                    # Alpine.js ya movió la tarjeta visualmente (Optimistic UI)
                    return HttpResponse(status=200)
            except Exception as e:
                logger.error(f"Error moviendo tarjeta Kanban: {e}")
                return HttpResponse("Error", status=400)

        return HttpResponse("Bad Request", status=400)

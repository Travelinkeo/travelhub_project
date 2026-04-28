import logging
from django.views import View
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin

# Importamos el modelo que creaste anteriormente
from apps.crm.models import OportunidadViaje

logger = logging.getLogger(__name__)

class KanbanBoardView(LoginRequiredMixin, View):
    """
    Renderiza el tablero principal de ventas, agrupando los leads por etapa.
    """
    template_name = 'crm/kanban_board.html'

    def get(self, request, *args, **kwargs):
        # Obtenemos todos los leads, optimizando la consulta del cliente
        leads = OportunidadViaje.objects.select_related('cliente').all().order_by('-creado_en')
        
        context = {
            'leads_new': leads.filter(etapa='NEW'),
            'leads_quo': leads.filter(etapa='QUO'),
            'leads_pay': leads.filter(etapa='PAY'),
            'leads_won': leads.filter(etapa='WON'),
        }
        return render(request, self.template_name, context)

class UpdateLeadStageView(LoginRequiredMixin, View):
    """
    Endpoint reactivo (HTMX). Recibe el ID del Lead y su nueva etapa
    cuando el usuario suelta la tarjeta (Drop).
    """
    def post(self, request, *args, **kwargs):
        lead_id = request.POST.get('lead_id')
        new_stage = request.POST.get('new_stage')
        
        if lead_id and new_stage:
            try:
                lead = get_object_or_404(OportunidadViaje, id=lead_id)
                
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
                return HttpResponse('Error', status=400)
                
        return HttpResponse('Bad Request', status=400)

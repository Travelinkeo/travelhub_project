import logging
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from apps.finance.services.ai_accounting_service import AIAccountingService
from apps.finance.models import DiferenciaFinanciera

logger = logging.getLogger(__name__)

class AIAccountingDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'finance/accounting_assistant.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ua = self.request.user.agencias.filter(activo=True).first()
        context['user_agencia'] = ua.agencia if ua else None
        return context

class AIAccountingChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Endpoint para interactuar con el Asistente Financiero.
        Payload: {"message": "Pregunta del usuario"}
        """
        user_message = request.data.get('message')
        if not user_message:
            return Response({"error": "Mensaje requerido"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Check Agency Context
            agencia = getattr(request, 'agencia', None)
            if not agencia:
                ua = request.user.agencias.filter(activo=True).first()
                if ua: 
                    agencia = ua.agencia
            
            if not agencia:
                 return Response({"error": "No tienes una agencia activa asociada."}, status=status.HTTP_403_FORBIDDEN)

            from apps.finance.services.ai_accounting_service import AIAccountingService
            service = AIAccountingService(agencia)
            response_text = service.ask(user_message)
            
            return Response({
                "response": response_text,
                "agency": agencia.nombre
            })

        except Exception as e:
            logger.exception("Error en AI Chat View")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AIChatHTMXView(LoginRequiredMixin, View):
    """
    Versión para HTMX del Chat AI que retorna fragmentos HTML.
    """
    def post(self, request):
        user_message = request.POST.get('message')
        if not user_message:
            return HttpResponse("", status=400)

        agencia = getattr(request, 'agencia', None)
        if not agencia:
            ua = request.user.agencias.filter(activo=True).first()
            if ua: agencia = ua.agencia
        
        if not agencia:
            return render(request, 'finance/partials/ai_chat_message.html', {
                "role": "assistant",
                "content": "No tienes una agencia activa asociada para realizar consultas financieras."
            })

        try:
            # Usamos el servicio robusto y unificado de Contabilidad
            from apps.finance.services.ai_accounting_service import AIAccountingService
            service = AIAccountingService(agencia)
            response_text = service.ask(user_message)
            
            return render(request, 'finance/partials/ai_chat_message.html', {
                "role": "assistant",
                "content": response_text
            })

        except Exception as e:
            logger.exception("Error en AI Chat HTMX")
            return render(request, 'finance/partials/ai_chat_message.html', {
                "role": "assistant",
                "content": f"Error técnico: {str(e)}"
            })

class ResolveDiscrepancyAIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        """
        Analiza una discrepancia financiera usando el Asistente Contable AI.
        Retorna un fragmento de HTML para ser inyectado por HTMX.
        """
        diferencia = get_object_or_404(DiferenciaFinanciera, pk=pk)
        item = diferencia.item_reporte
        
        agencia = getattr(request, 'agencia', None)
        if not agencia:
            ua = request.user.agencias.filter(activo=True).first()
            if ua: agencia = ua.agencia
        
        if not agencia:
            return render(request, 'finance/reconciliation/partials/ai_analysis_error.html', 
                         {"error": "No hay agencia activa asociada."})

        try:
            from apps.finance.services.ai_accounting_service import AIAccountingService
            assistant = AIAccountingService(agencia)
            # Pedimos a la IA que analice el boleto
            explicacion = assistant.ask(f"Analiza la discrepancia del boleto {item.numero_boleto} y explicame que paso.")
            
            # Pedimos una propuesta de asiento
            propuesta_json = assistant.propose_accounting_entry("Boleto", item.id)
            import json
            propuesta = json.loads(propuesta_json)

            context = {
                "item": item,
                "diferencia": diferencia,
                "explicacion": explicacion,
                "propuesta": propuesta
            }
            return render(request, 'finance/reconciliation/partials/ai_analysis.html', context)
            
        except Exception as e:
            logger.exception(f"Error analizando discrepancia {pk}")
            return render(request, 'finance/reconciliation/partials/ai_analysis_error.html', 
                         {"error": f"Error técnico: {str(e)}"})

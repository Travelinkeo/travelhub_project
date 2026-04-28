import logging
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from apps.crm.models import Cliente, MensajeWhatsApp
from core.services.ai_engine import ai_engine

logger = logging.getLogger(__name__)

class GenerateSuggestedReplyView(LoginRequiredMixin, View):
    """
    Vista IA para generar respuestas sugeridas.
    Gemini lee el historial de chat y devuelve opciones.
    """
    def get(self, request, cliente_id, *args, **kwargs):
        cliente = get_object_or_404(Cliente, pk=cliente_id)
        
        # 1. Obtener los últimos mensajes del chat para contexto
        ultimos_mensajes = cliente.mensajes_whatsapp.all().order_by('-timestamp')[:10]
        contexto_chat = "\n".join([
            f"{'Cliente' if m.direccion == 'IN' else 'Agencia'}: {m.texto}" 
            for m in reversed(ultimos_mensajes)
        ])
        
        if not contexto_chat:
            return JsonResponse({"error": "No hay mensajes para analizar"}, status=400)

        # 2. Instrucciones para Gemini
        prompt_ia = f"""
        Actúa como un experto asesor de ventas de TravelHub. Lee el siguiente historial de chat y genera exactamente 2 sugerencias de respuesta para el agente humano.
        
        HISTORIAL DE CHAT:
        {contexto_chat}
        
        REGLAS:
        - Sé breve, profesional y persuasivo.
        - Usa emojis amigables.
        - Devuelve exactamente 2 opciones separadas por un separador especial |OPCION|
        - No inventes precios ni servicios que no se mencionen arriba.
        """
        
        try:
            # 3. Llamada a Gemini
            resultado = ai_engine.call_gemini(
                prompt=prompt_ia,
                system_instruction="Eres un asistente de redacción para agentes de viajes."
            )
            
            # 4. Procesar respuesta
            texto_ia = resultado.get('text', '') if isinstance(resultado, dict) else str(resultado)
            opciones = [o.strip().replace('"', '') for o in texto_ia.split('|OPCION|') if o.strip()]

            # 5. Renderizar Parcial HTML (para HTMX)
            from django.shortcuts import render
            return render(request, "crm/inbox/partials/ai_suggestions.html", {
                "sugerencias": opciones[:2] if opciones else ["Chat analizado. ¿En qué podemos ayudarte?", "Entendido, procedemos con la gestión."]
            })
            
        except Exception as e:
            logger.error(f"Error GenerateSuggestedReplyView AI: {e}")
            return HttpResponse("Error cargando sugerencias", status=500)

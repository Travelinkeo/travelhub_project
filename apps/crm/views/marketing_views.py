import logging
import json
from django.views import View
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin

from apps.crm.services.marketing_service import MarketingAIEngine
from apps.crm.tasks_marketing import despachar_campana_masiva_task

logger = logging.getLogger(__name__)

class MarketingHubView(LoginRequiredMixin, View):
    """ Renderiza la pantalla principal del Hub de Marketing """
    template_name = 'crm/marketing/hub.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

class AnalyzeCampaignPromptView(LoginRequiredMixin, View):
    """ Endpoint HTMX que procesa el prompt con IA y devuelve el preview """
    def post(self, request, *args, **kwargs):
        prompt = request.POST.get('prompt_marketing')

        if not prompt or len(prompt) < 10:
            return HttpResponse('<div class="text-red-500 font-bold p-4 bg-red-50 rounded-xl">Por favor, sé más específico en tu solicitud a la IA.</div>')

        resultado = MarketingAIEngine.procesar(prompt)

        if "error" in resultado:
            return HttpResponse(f'<div class="text-red-500 font-bold p-4 bg-red-50 rounded-xl">Error IA: {resultado["error"]}</div>')

        modo = resultado.get('modo', 'creativo')

        # ── MODO CREATIVO: branding, copy, posts, slogans ──────────────────────
        if modo == 'creativo':
            context = {'contenido': resultado.get('contenido', {})}
            return render(request, 'crm/marketing/partials/creative_preview.html', context)

        # ── MODO CAMPAÑA: envío masivo a clientes ──────────────────────────────
        if resultado['total_audiencia'] == 0:
            return HttpResponse("""
            <div class="bg-amber-50 border border-amber-200 p-6 rounded-2xl text-center">
                <span class="material-symbols-outlined text-4xl text-amber-500 mb-2">group_off</span>
                <h3 class="text-lg font-black text-amber-900">Sin Audiencia Detectada</h3>
                <p class="text-amber-700 text-sm">Gemini configuró tu campaña, pero no encontramos clientes en la base de datos que cumplan estos requisitos. Intenta ser menos restrictivo.</p>
            </div>
            """)

        cliente_ids = resultado.get('cliente_ids', [])
        context = {
            'ia_data': resultado['ia_data'],
            'total_audiencia': resultado['total_audiencia'],
            'clientes_muestra': resultado['clientes_target'][:5],
            'cliente_ids_json': json.dumps(cliente_ids),
        }
        return render(request, 'crm/marketing/partials/campaign_preview.html', context)


class DispatchCampaignView(LoginRequiredMixin, View):
    """ Endpoint HTMX que recibe el OK del agente y encola los correos en Celery """
    def post(self, request, *args, **kwargs):
        asunto = request.POST.get('asunto')
        cuerpo_html = request.POST.get('cuerpo_html')
        cliente_ids_json = request.POST.get('cliente_ids')
        
        try:
            cliente_ids = json.loads(cliente_ids_json or '[]')
            
            # 🚀 DISPARAR CELERY
            despachar_campana_masiva_task.apply_async(
                args=[cliente_ids, asunto, cuerpo_html],
                queue='notifications'
            )
            
            html_exito = """
            <div class="bg-emerald-50 border border-emerald-200 p-8 rounded-3xl text-center animate-fade-in-up">
                <div class="w-20 h-20 bg-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg shadow-emerald-500/30">
                    <span class="material-symbols-outlined text-white text-4xl">send</span>
                </div>
                <h3 class="text-2xl font-black text-emerald-900 mb-2">¡Campaña en el aire!</h3>
                <p class="text-emerald-700 font-medium mb-6">Gemini ha entregado la campaña a Celery. Los correos se están enviando silenciosamente en segundo plano.</p>
                <div class="flex justify-center">
                   <button onclick="location.reload()" class="bg-slate-900 text-white font-bold py-2 px-6 rounded-xl hover:bg-slate-800 transition-colors">Crear Nueva Campaña</button>
                </div>
            </div>
            """
            return HttpResponse(html_exito)
            
        except Exception as e:
            return HttpResponse(f'<div class="text-red-500 font-bold">Error despachando: {e}</div>')

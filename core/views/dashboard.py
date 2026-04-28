import logging
import json
import time
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
from core.services.bi_service import BusinessIntelligenceEngine
from core.services.ai_engine import ai_engine
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# --- ESQUEMAS IA ---
class ConsejosIASchema(BaseModel):
    saludo: str = Field(description="Un saludo enérgico para el CEO (ej. '¡Buen día, equipo directivo!')")
    diagnostico: str = Field(description="Un diagnóstico de 1 línea basado en las métricas")
    consejo_estrategico: str = Field(description="Un consejo de negocio basado en si las ventas suben o bajan")
    accion_recomendada: str = Field(description="Una recomendación directa (ej. 'Inicia trámites de Tax Refund para flujo de caja extra')")

# --- UTILS ---
def _get_active_agencia(user):
    """Helper para obtener la agencia activa del usuario."""
    if not user.is_authenticated:
        return None
    
    # 1. Buscar en relación UsuarioAgencia (SaaS / Staff)
    ua = user.agencias.filter(activo=True).first()
    if ua:
        return ua.agencia
        
    # 2. Buscar en Perfil de Freelancer (Agentes externos)
    if hasattr(user, 'perfil_freelancer'):
        return user.perfil_freelancer.agencia
        
    return None

# --- VISTAS ---
class CEODashboardView(LoginRequiredMixin, View):
    """
    Centro de Mando del CEO (Dashboard Directivo).
    Carga KPIs financieros y gráficos consolidados.
    """
    template_name = 'core/dashboard_ceo.html'

    def get(self, request, *args, **kwargs):
        agencia = _get_active_agencia(request.user)
        if not agencia:
            return render(request, 'errors/no_agency.html', {
                'message': "No tienes una agencia activa asociada a tu cuenta."
            })

        kpis = BusinessIntelligenceEngine.obtener_kpis_ceo(agencia)
        
        # Obtenemos también los datos para el gráfico
        chart_data = BusinessIntelligenceEngine.get_monthly_sales_chart_data(agencia)

        context = {
            'kpis': kpis,
            'agencia': agencia,
            'chart_data_json': mark_safe(json.dumps(chart_data))
        }
        return render(request, self.template_name, context)

class AIBusinessAdvisorView(LoginRequiredMixin, View):
    """
    Endpoint HTMX (Lazy Load) para generar un diagnóstico estratégico usando Gemini AI.
    """
    def get(self, request, *args, **kwargs):
        agencia = _get_active_agencia(request.user)
        if not agencia:
            return HttpResponse("No se detectó agencia.", status=400)

        kpis = BusinessIntelligenceEngine.obtener_kpis_ceo(agencia)
        
        prompt = f"""
        Eres el Asesor Financiero IA (TravelHub BI) de una agencia de viajes.
        Analiza estas métricas del mes actual:
        - Ventas del mes: ${kpis['ventas_mes_actual']}
        - Crecimiento vs mes pasado: {kpis['crecimiento_porcentaje']}%
        - Utilidad bruta: ${kpis['utilidad_bruta']}
        - Dinero en la mesa (Tax Refund): ${kpis['tax_refund_disponible']}
        
        Dame un diagnóstico rápido y un consejo accionable basado en rentabilidad.
        """
        
        try:
            # God Mode: Extracción estructurada con Gemini 1.5 Flash/Pro
            resultado = ai_engine.parse_structured_data(
                text=prompt,
                schema=ConsejosIASchema,
                system_prompt="Eres un consultor experto en rentabilidad y CFO virtual para agencias de viaje B2B."
            )
            
            return render(request, 'core/partials/ai_insight_card.html', {'insight': resultado})
            
        except Exception as e:
            logger.error(f"Error generando consejo de CEO: {e}")
            return HttpResponse('<div class="p-4 text-red-500 text-xs italic">El asesor IA está procesando otros datos. Reintenta en breve.</div>')

import logging
import os

from django.conf import settings

from .ai_tools import AgentTools

logger = logging.getLogger(__name__)

def _get_genai():
    from google import genai
    return genai

def _get_genai_types():
    from google.genai import types
    return types

class TravelHubAgent:
    """
    Agente IA de TravelHub v2 (Basado en Gemini Function Calling).
    Capaz de consultar datos reales de contabilidad, ventas y clientes.
    """
    
    def __init__(self, agency=None):
        from apps.automation.services.ai_engine import get_gemini_api_key
        api_key = get_gemini_api_key(agency)
        if not api_key:
            logger.error("TravelHubAgent: GEMINI_API_KEY no configurada.")
            raise ValueError("Falta GEMINI_API_KEY")
            
        genai = _get_genai()
        self.client = genai.Client(api_key=api_key)
        self.model_name = 'gemini-2.0-flash'
        self.history = []

        self.tools = [
            AgentTools.get_sales_stats,
            AgentTools.get_financial_kpis,
            AgentTools.get_pending_payments,
            AgentTools.get_financial_report,
            AgentTools.get_client_info,
            AgentTools.get_quote_status,
            AgentTools.get_recent_expenses,
            AgentTools.generate_cms_content,
            AgentTools.list_cms_content,
            AgentTools.get_reconciliation_summary,
            AgentTools.get_reconciliation_discrepancies,
            AgentTools.get_cash_flow_summary,
            AgentTools.get_cashflow_forecast,
            AgentTools.get_account_balance,
            AgentTools.generate_marketing_copy,
        ]
        
        self._system_prompt = self._get_system_prompt()

    def _get_system_prompt(self) -> str:
        return """
        Eres el Agente Inteligente de TravelHub, el cerebro contable y operativo de Travelinkeo.
        Tu misión es ayudar a los agentes de viajes y contadores a gestionar la agencia de forma eficiente.
        
        TIENES ACCESO A DATOS REALES:
        - Puedes consultar estadísticas de ventas.
        - Puedes ver facturas y pagos pendientes.
        - Puedes generar reportes financieros (P&L, Balance).
        - Puedes buscar información de clientes y estados de PNR.
        - Puedes consultar los gastos operativos recientes.
        - Puedes gestionar el CMS: listar contenido existente y guardar nuevos borradores generados por ti.
        - Puedes analizar reportes de conciliación de proveedores y encontrar discrepancias.
        - Puedes dar resúmenes de flujo de caja e incluso PROYECCIONES (forecast) a 30 días usando 'get_cashflow_forecast'.
        - Puedes consultar el saldo y naturaleza de cualquier cuenta contable usando 'get_account_balance'.
        - Puedes generar paquetes de marketing (captions, hashtags, mejores horarios) para hoteles específicos usando 'generate_marketing_copy'.
        
        REGLAS DE COMPORTAMIENTO:
        1. Siempre responde en español venezolano (amigable, profesional, usa 'pana', 'epa', 'chévere', 'brutal').
        2. Si te preguntan por el flujo de dinero general, usa 'get_cash_flow_summary' o 'get_cashflow_forecast'.
        3. Si te piden analizar por qué un reporte de proveedor no cuadra, usa 'get_reconciliation_summary' y luego 'get_reconciliation_discrepancies' para boletos específicos.
        4. Para KPIs rápidos de utilidad y ventas del mes, usa 'get_financial_kpis'.
        5. Si te piden escribir un artículo para el blog, genera tú el contenido Markdown y luego guárdalo usando 'generate_cms_content'.
        6. Si te piden un post para redes sociales o promocionar un hotel, usa 'generate_marketing_copy'.
        7. No inventes datos. Si no encuentras algo, dilo claramente.
        8. Usa Markdown para dar formato a tus respuestas, especialmente tablas y listas.
        9. Si una operación es exitosa o las ventas van bien, felicita al usuario con entusiasmo.
        """

    def process_query(self, user_message: str):
        """
        Procesa una consulta del usuario usando Gemini con function calling.
        """
        try:
            self.history.append({"role": "user", "parts": [{"text": user_message}]})

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=self.history,
                config=types.GenerateContentConfig(
                    system_instruction=self._system_prompt,
                    tools=self.tools,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        maximum_remote_calls=10
                    ),
                )
            )

            reply = response.text
            self.history.append({"role": "model", "parts": [{"text": reply}]})
            return reply
        except Exception as e:
            logger.error(f"Error en TravelHubAgent: {str(e)}", exc_info=True)
            return f"Epa, tuve un problemita técnico procesando eso: {str(e)}"
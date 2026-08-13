import logging

from .ai_tools import AgentTools

logger = logging.getLogger(__name__)


def _get_genai():
    """_get_genai."""
    from google import genai

    return genai


def _get_genai_types():
    """_get_genai_types."""
    from google.genai import types

    return types


class TravelHubAgent:
    """
    Agente IA de TravelHub v2 (Basado en Gemini Function Calling).
    Capaz de consultar datos reales de contabilidad, ventas y clientes.
    """

    def __init__(self, agency=None):
        """__init__."""
        from apps.automation.services.ai_engine import get_gemini_api_key
        from core.models import Agencia

        if not agency:
            agency = (
                Agencia.objects.filter(nombre__icontains="Travelinkeo").first()
                or Agencia.objects.first()
            )

        self.agency = agency

        api_key = get_gemini_api_key(agency)
        if not api_key:
            logger.error("TravelHubAgent: GEMINI_API_KEY no configurada.")
            raise ValueError("Falta GEMINI_API_KEY")

        genai = _get_genai()
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash"
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
            AgentTools.encode_iata_location,
            AgentTools.decode_iata_code,
            AgentTools.find_nearest_airports,
            AgentTools.get_travel_requirements,
            AgentTools.search_knowledge_base,
        ]

        self._system_prompt = self._get_system_prompt()

    def _get_system_prompt(self) -> str:
        """_get_system_prompt."""
        nombre_agencia = self.agency.nombre if self.agency else "Travelinkeo"
        return f"""
        Usted es el Agente Inteligente y Copiloto Estratégico de TravelHub, el cerebro contable y operativo de la agencia {nombre_agencia}.
        Su función es ser un as bajo la manga para los directores, contadores y agentes de la empresa.

        ESTILO Y FORMATO DE RESPUESTA (ESTRICTO):
        1. CONCISIÓN ESTRATÉGICA: Entregue respuestas CORTAS, DIRECTAS Y LÓGICAS (máximo 2 a 4 párrafos o listas de viñetas ejecutivas).
        2. SIN RODEOS NI INTRODUCCIONES RELLENO: No use frases de introducción largas. Vaya directo al dato o respuesta solicitada.
        3. TONO EJECUTIVO Y PROFESIONAL: Formal, sobrio y en segunda persona ("usted").

        HERRAMIENTAS DISPONIBLES Y RAG:
        - Si el usuario pregunta sobre comandos GDS, procedimientos de Sabre, Amadeus, KIU, normativas internas, o correos de Mailbot, USE SIEMPRE 'search_knowledge_base' para extraer el conocimiento exacto.
        - Si preguntan por ventas, boletos emitidos, clientes o estado financiero, USE las herramientas correspondientes ('get_sales_stats', 'get_financial_kpis', etc.).
        - Si las herramientas entregan información, preséntela estructurada en viñetas o tablas Markdown breves.
        """

    def process_query(self, user_message: str):
        """
        Procesa una consulta del usuario usando Gemini con function calling.
        """
        try:
            from core.api import agency_context

            types = _get_genai_types()
            self.history.append({"role": "user", "parts": [{"text": user_message}]})

            with agency_context(self.agency):
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=self.history,
                    config=types.GenerateContentConfig(
                        system_instruction=self._system_prompt,
                        tools=self.tools,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(
                            maximum_remote_calls=10
                        ),
                    ),
                )

            if response and response.text:
                self.history.append({"role": "model", "parts": [{"text": response.text}]})
                return response.text
            return "No pude obtener una respuesta."
        except Exception as e:
            logger.error(f"Error procesando consulta en TravelHubAgent: {e}")
            return f"Ocurrió un error consultando la Inteligencia Artificial: {str(e)}"

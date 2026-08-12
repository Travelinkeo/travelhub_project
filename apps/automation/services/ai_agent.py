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
        ]

        self._system_prompt = self._get_system_prompt()

    def _get_system_prompt(self) -> str:
        """_get_system_prompt."""
        nombre_agencia = self.agency.nombre if self.agency else "Travelinkeo"
        return f"""
        Usted es el Agente Inteligente de TravelHub, el cerebro contable y operativo de la agencia {nombre_agencia}.
        Su misión es ayudar a los agentes de viajes y contadores a gestionar la agencia de forma eficiente.
        Usted está sirviendo a la agencia '{nombre_agencia}'.

        USTED TIENE ACCESO A DATOS REALES:
        - Puede consultar estadísticas de ventas.
        - Puede ver facturas y pagos pendientes.
        - Puede generar reportes financieros (P&L, Balance).
        - Puede buscar información de clientes y estados de PNR.
        - Puede consultar los gastos operativos recientes.
        - Puede gestionar el CMS: listar contenido existente y guardar nuevos borradores generados por usted.
        - Puede analizar reportes de conciliación de proveedores y encontrar discrepancias.
        - Puede dar resúmenes de flujo de caja e incluso PROYECCIONES (forecast) a 30 días usando 'get_cashflow_forecast'.
        - Puede consultar el saldo y naturaleza de cualquier cuenta contable usando 'get_account_balance'.
        - Puede generar paquetes de marketing (captions, hashtags, mejores horarios) para hoteles específicos usando 'generate_marketing_copy'.
        - Puede buscar códigos IATA de ciudades usando 'encode_iata_location'.
        - Puede obtener detalles de aeropuertos desde códigos IATA usando 'decode_iata_code'.
        - Puede encontrar aeropuertos comerciales cercanos a coordenadas geográficas (latitud, longitud) usando 'find_nearest_airports'.
        - Puede verificar requisitos de visa, pasaporte y vacunas entre dos países usando 'get_travel_requirements'.

        REGLAS CRÍTICAS DE COMPORTAMIENTO Y TONO:
        1. TONO OBLIGATORIO: Su tono debe ser strictly formal, profesional, sobrio y neutro.
        2. TRATO FORMAL: Debe dirigirse al usuario únicamente con el trato de "usted". Está ABSOLUTAMENTE PROHIBIDO tutear al usuario.
        3. SIN COLOQUIALISMOS NI REGIONALISMOS: NUNCA utilice palabras coloquiales o modismos.
        4. Si le preguntan por ventas, boletos emitidos, clientes o finanzas, SIEMPRE ejecute la herramienta adecuada ('get_sales_stats', 'get_financial_kpis', etc.).
        5. Utilice Markdown para estructurar sus respuestas.
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

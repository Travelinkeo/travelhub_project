# ==============================================================================
# 🧠 MOTORES DE INTELIGENCIA ARTIFICIAL EN TRAVELHUB: VIRTUAL CFO CHAT
# ==============================================================================
# ESTE ARCHIVO: 'ai_accounting_service.py' (AIAccountingService)
# ROL: Asistente financiero e interactivo para chat y consultas complejas.
# PRINCIPAL CARACTERÍSTICA: Interactivo. Utiliza Gemini chats con herramientas
# dinámicas (Function Calling) para responder y ejecutar tareas en tiempo real.
#
# NOTA DE DISEÑO: No confundir con 'accounting_ai_service.py' (AccountingAIService),
# el cual es el motor (CPA Engine) no interactivo de generación física de asientos.
# ==============================================================================

import json
import logging

from core.api import agency_context

logger = logging.getLogger(__name__)


class AIAccountingService:
    """
    Servicio de Asistente Financiero y Contable con IA (Gemini Pro/Flash).
    Utiliza Function Calling para interactuar con el ERP en tiempo real.
    """

    def __init__(self, agencia):
        """__init__."""
        self.agencia = agencia
        from django.utils.module_loading import import_string
        from google import genai

        get_gemini_api_key = import_string("apps.automation.services.ai_engine.get_gemini_api_key")

        self.api_key = get_gemini_api_key(agencia)
        self.client = genai.Client(api_key=self.api_key)
        self.model_id = "gemini-2.5-flash"

        AgentTools = import_string("apps.automation.services.ai_tools.AgentTools")
        # Lista de herramientas disponibles para la IA
        self.tools = [
            AgentTools.get_sales_stats,
            AgentTools.get_financial_kpis,
            AgentTools.get_pending_payments,
            AgentTools.get_financial_report,
            AgentTools.get_client_info,
            AgentTools.get_quote_status,
            AgentTools.get_recent_expenses,
            AgentTools.get_reconciliation_summary,
            AgentTools.get_cash_flow_summary,
            AgentTools.get_account_balance,
            AgentTools.get_cashflow_forecast,
            AgentTools.get_reconciliation_discrepancies,
            AgentTools.run_reconciliation,
            AgentTools.propose_manual_journal_entry,
        ]

    def ask(self, user_message: str) -> str:
        """
        Inicia una sesión de chat con Function Calling automático.
        """
        try:
            from django.utils.module_loading import import_string

            CFO_VIRTUAL_SYSTEM_PROMPT = import_string(
                "apps.automation.services.prompts.CFO_VIRTUAL_SYSTEM_PROMPT"
            )

            # Asegurar que el contexto de la agencia esté seteado para AgentTools
            with agency_context(self.agencia):
                # Configuración del chat con herramientas
                chat = self.client.chats.create(
                    model=self.model_id,
                    config={
                        "system_instruction": CFO_VIRTUAL_SYSTEM_PROMPT,
                        "tools": self.tools,
                    },
                )

                response = chat.send_message(user_message)

                # El SDK de google-genai maneja las llamadas a funciones de forma automática
                # en el objeto chat si se configura correctamente.

                return response.text

        except Exception as e:
            logger.error(f"Error en AIAccountingService.ask: {e}", exc_info=True)
            return f"Lo siento, ocurrió un error procesando tu solicitud financiera: {str(e)}"

    def propose_accounting_entry(self, documento_tipo: str, documento_id: int):
        """Genera una propuesta de asiento para una Factura o Gasto (Lógica legacy)."""
        return json.dumps(
            {
                "propuesta": "Asiento sugerido generado",
                "glosa": f"Registro de {documento_tipo} ID {documento_id}",
                "detalles": [
                    {"cuenta": "1.1.01.01", "desc": "Caja/Bancos", "debe": 100.0, "haber": 0},
                    {
                        "cuenta": "4.1.01.01",
                        "desc": "Ingresos por Servicios",
                        "debe": 0,
                        "haber": 100.0,
                    },
                ],
            }
        )

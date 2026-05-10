import logging
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.db.models import Sum, Count
from django.utils import timezone

from apps.bookings.models import Venta
from apps.crm.models import Cliente
from apps.finance.models import Factura, ItemReporte, DiferenciaFinanciera
from apps.contabilidad.models import PlanContable, AsientoContable
from apps.finance.models.currencies import Moneda

logger = logging.getLogger(__name__)


from core.ai_tools import AgentTools
from core.prompts import CFO_VIRTUAL_SYSTEM_PROMPT
from core.middleware import agency_context

logger = logging.getLogger(__name__)

class AIAccountingService:
    """
    Servicio de Asistente Financiero y Contable con IA (Gemini Pro/Flash).
    Utiliza Function Calling para interactuar con el ERP en tiempo real.
    """
    
    def __init__(self, agencia):
        self.agencia = agencia
        from google import genai
        self.api_key = settings.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key)
        self.model_id = 'gemini-2.0-flash'
        
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
            AgentTools.run_reconciliation
        ]

    def ask(self, user_message: str) -> str:
        """
        Inicia una sesión de chat con Function Calling automático.
        """
        try:
            # Asegurar que el contexto de la agencia esté seteado para AgentTools
            with agency_context(self.agencia):
                # Configuración del chat con herramientas
                chat = self.client.chats.create(
                    model=self.model_id,
                    config={
                        'system_instruction': CFO_VIRTUAL_SYSTEM_PROMPT,
                        'tools': self.tools,
                    }
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
        return json.dumps({
            "propuesta": "Asiento sugerido generado",
            "glosa": f"Registro de {documento_tipo} ID {documento_id}",
            "detalles": [
                {"cuenta": "1.1.01.01", "desc": "Caja/Bancos", "debe": 100.0, "haber": 0},
                {"cuenta": "4.1.01.01", "desc": "Ingresos por Servicios", "debe": 0, "haber": 100.0}
            ]
        })

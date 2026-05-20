# ==============================================================================
# 🧠 SERVICIOS DE INTELIGENCIA ARTIFICIAL CONTABLE (TRAVELHUB FINANCE)
# ==============================================================================
# Este submódulo expone los dos servicios de inteligencia artificial del ERP
# que operan sobre el módulo contable y financiero.
#
# ROL DE CADA SERVICIO:
#
# 1. AccountingAIService (de 'accounting_ai_service.py')
#    -> El "CPA Engine". Motor determinístico de partida doble.
#    -> Recibe descripciones de transacciones y genera asientos contables físicos.
#    -> No-interactivo. Estrictamente estructurado usando esquemas Pydantic.
#
# 2. AIAccountingService (de 'ai_accounting_service.py')
#    -> El "Virtual CFO". Asistente de chat financiero interactivo.
#    -> Utiliza chats de Gemini con Function Calling (AgentTools) para consultas vivas.
#    -> Interactivo. Permite al usuario dialogar y ejecutar acciones sobre el ERP.
# ==============================================================================

from .accounting_ai_service import AccountingAIService
from .ai_accounting_service import AIAccountingService

__all__ = [
    "AccountingAIService",
    "AIAccountingService",
]

# apps/finance/services/accounting_assistant.py
from .ai_accounting_service import AIAccountingService


class AccountingAssistantService(AIAccountingService):
    """
    Subclass/Alias of AIAccountingService to satisfy legacy test scripts
    and ensure correct name mapping for the AI Accounting Assistant.
    """

    pass

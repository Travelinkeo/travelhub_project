import logging
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from .ai_engine import ai_engine

logger = logging.getLogger(__name__)

from core.models.ai_schemas import AuditReport

class AuditService:
    """
    Servicio de auditoría preventiva para boletos basado en IA.
    Aplica reglas de negocio de TravelHub.
    """
    
    RULES_PROMPT = """
    Eres un Auditor de Emisión de Boletos Aéreos para la agencia TravelHub.
    Tu tarea es revisar los datos de un boleto y verificar que cumplan con las siguientes reglas:

    1. REGALAS DE FEES (CARGOS DE SERVICIO):
       - Vuelos Internacionales: Cargo de $15 USD por cada segmento de vuelo.
       - Vuelos Domésticos (Venezuela): Cargo de $5 USD por cada segmento de vuelo.
       - Otros productos o servicios (Hoteles, Autos, Seguros): 10% del valor neto del proveedor + Fee del proveedor + 3% IGTF.

    2. REGLAS DE FORMATO:
       - Nombre del Pasajero: Debe seguir el formato estándar de GDS 'APELLIDO/NOMBRE'.
       - Impuesto INATUR: Debe ser exactamente el 1% de la Tarifa Base si el vuelo es nacional (Venezuela).

    3. REGLAS DE COHERENCIA:
       - El número de boleto debe tener 13 dígitos.
       - El localizador (PNR) debe tener 6 caracteres alfanuméricos.

    INSTRUCCIONES DE SALIDA:
    Debes retornar un JSON estructurado según el esquema AUDIT_REPORT.
    Calcula los fees sugeridos basándote en el número de segmentos detectados en el itinerario.
    """

    def audit_ticket_data(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la auditoría sobre los datos de un boleto.
        """
        if not ai_engine.is_ready:
            return {"error": "IA no disponible para auditoría."}

        prompt = f"Realiza la auditoría para los siguientes datos de boleto:\n{json.dumps(ticket_data, indent=2)}"
        
        try:
            report = ai_engine.call_gemini(
                prompt=prompt,
                system_instruction=self.RULES_PROMPT,
                response_schema=AuditReport
            )
            return report
        except Exception as e:
            logger.error(f"Error en AuditService: {e}")
            return {"error": str(e)}

audit_service = AuditService()

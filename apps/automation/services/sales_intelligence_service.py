import logging
from typing import Any

from pydantic import BaseModel, Field

from apps.automation.services.ai_engine import ai_engine

logger = logging.getLogger(__name__)


class UpsellingOpportunity(BaseModel):
    """UpsellingOpportunity."""

    product_type: str = Field(
        description="Tipo de producto sugerido (Hotel, Seguro, Traslado, Tour, etc.)"
    )
    rationale: str = Field(description="Por qué estamos sugiriendo esto basado en el itinerario")
    marketing_copy: str = Field(
        description="Un gancho de venta de 1 línea para enviarle al cliente"
    )
    estimated_revenue: str = Field(description="Rango de ingreso estimado (ej. '$50 - $200')")


class SalesIntelligenceReport(BaseModel):
    """SalesIntelligenceReport."""

    summary: str = Field(description="Resumen de la estrategia de venta para este boleto")
    opportunities: list[UpsellingOpportunity] = Field(
        description="Lista de productos complementarios"
    )
    urgency_score: int = Field(description="Nivel de urgencia de contacto (1-10)", ge=1, le=10)


class SalesIntelligenceService:
    """
    Motor Proactivo de Inteligencia de Ventas.
    Transforma boletos en oportunidades de negocio usando IA.
    """

    @classmethod
    def analyze_booking_for_upselling(
        cls, ticket_data: dict[str, Any], agencia=None
    ) -> dict[str, Any]:
        """
        Analiza la data de un boleto procesado y genera una estrategia de upselling.
        """
        try:
            itinerario = ticket_data.get("itinerario", [])
            pasajero = ticket_data.get("pasajeros", [{}])[0]
            nombre_pax = pasajero.get("nombre", "Pasajero")
            total_ticket = ticket_data.get("tarifas", {}).get("total", 0)

            # Construir contexto para la IA
            destinos = [
                seg.get("destino_ciudad") for seg in itinerario if seg.get("destino_ciudad")
            ]
            fechas = [seg.get("fecha") for seg in itinerario if seg.get("fecha")]

            prompt = f"""
            Actúa como un Gerente de Ventas de Viajes experto.
            He procesado un nuevo boleto de avión para {nombre_pax}.
            Detalles:
            - Destinos: {", ".join(destinos)}
            - Fechas: {", ".join(fechas)}
            - Valor del vuelo: ${total_ticket}
            - Agencia: {agencia.nombre if agencia else "TravelHub"}

            Tu objetivo es identificar 3 oportunidades de upselling (venta cruzada) para maximizar la rentabilidad de este viaje.
            Considera factores como: longitud del vuelo, tipo de destino (vacacional vs negocios), y necesidades logísticas obvias.
            """

            report = ai_engine.parse_structured_data(
                text=prompt,
                schema=SalesIntelligenceReport,
                system_prompt="Eres un motor de BI especializado en cross-selling turístico B2B/B2C.",
            )

            return report

        except Exception as e:
            logger.error(f"Error en analyze_booking_for_upselling: {e}")
            return {
                "summary": "Error analizando oportunidades",
                "opportunities": [],
                "urgency_score": 1,
            }

    @classmethod
    def format_report_for_display(cls, report: Any) -> str:
        """
        Formatea el reporte estructurado en texto limpio, profesional y legible para agentes.
        """
        if not report:
            return ""

        if hasattr(report, "model_dump"):
            data = report.model_dump()
        elif hasattr(report, "dict"):
            data = report.dict()
        elif isinstance(report, dict):
            data = report
        else:
            return str(report)

        summary = data.get("summary", "")
        opportunities = data.get("opportunities", [])
        urgency = data.get("urgency_score", None)

        lines = []
        if summary:
            lines.append(f"🎯 Estrategia Comercial:\n{summary}")

        if opportunities:
            lines.append("\n💡 Oportunidades de Venta Cruzada:")
            for op in opportunities:
                p_type = op.get("product_type", "Servicio Adicional")
                est_rev = op.get("estimated_revenue", "")
                rationale = op.get("rationale", "")
                copy = op.get("marketing_copy", "")

                rev_str = f" [Ingreso est: {est_rev}]" if est_rev else ""
                lines.append(f"• {p_type}{rev_str}:\n  {rationale}")
                if copy:
                    lines.append(f'  Gancho sugerido: "{copy}"')

        if urgency:
            lines.append(f"\n⚡ Nivel de Urgencia sugerido: {urgency}/10")

        return "\n".join(lines)

    @classmethod
    def get_destination_insight(cls, destination_city: str) -> str:
        """Obtiene un fun fact o tip de ventas sobre un destino específico."""
        prompt = f"Dame un consejo de venta rápido (1 línea) para un agente de viajes que está vendiendo {destination_city}."
        res = ai_engine.call_gemini(prompt=prompt)
        return res.get("text", "")

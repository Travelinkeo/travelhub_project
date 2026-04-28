import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
from pydantic import BaseModel, Field

from apps.bookings.models import Venta
from core.services.ai_engine import ai_engine

logger = logging.getLogger(__name__)

class ForecastInsight(BaseModel):
    title: str = Field(description="Título corto del insight (Ej: Auge en Caribe)")
    description: str = Field(description="Descripción detallada y recomendación estratégica")
    impact_level: str = Field(description="Nivel de impacto esperado: HIGH, MEDIUM, LOW")

class HotDestination(BaseModel):
    name: str = Field(description="Nombre del destino o país")
    growth_probability: str = Field(description="Probabilidad de crecimiento (Ej: 85%)")
    reason: str = Field(description="Razón breve de la tendencia")

class SalesForecastSchema(BaseModel):
    predicted_sales_next_month: str = Field(description="Monto predicho de ventas para el próximo mes")
    confidence_level: str = Field(description="Nivel de confianza de la predicción (Ej: 92%)")
    momentum_indicator: str = Field(description="Indicador de tendencia: UP, DOWN, STABLE")
    hot_destinations: List[HotDestination] = Field(description="Top 3-4 destinos recomendados")
    strategic_insights: List[ForecastInsight] = Field(description="Recomendaciones tácticas detalladas")

class AIForecastService:
    """
    Servicio de inteligencia de negocios que analiza datos históricos de ventas
    para predecir tendencias y ofrecer insights estratégicos usando Gemini.
    """

    def get_historical_data(self, months=12) -> List[Dict[str, Any]]:
        """
        Extrae datos agregados de ventas por mes.
        """
        start_date = timezone.now() - timedelta(days=30 * months)
        
        # Ventas por mes
        sales_by_month = (
            Venta.objects.filter(fecha_venta__gte=start_date)
            .annotate(month=TruncMonth('fecha_venta'))
            .values('month')
            .annotate(
                total=Sum('total_venta'),
                count=Count('id_venta')
            )
            .order_by('month')
        )
        
        # Tipos de venta más comunes (GDS vs Directo, etc)
        # Aquí simplificamos para el prompt
        data = []
        for entry in sales_by_month:
            data.append({
                "month": entry['month'].strftime("%Y-%m"),
                "total_sales": float(entry['total'] or 0),
                "transaction_count": entry['count']
            })
        
        return data

    def get_top_destinations_historical(self, months=6) -> List[str]:
        """
        Deduce destinos populares de los items de venta.
        """
        # Nota: En una implementación real, buscaríamos en SegmentoVuelo u HotelTarifario
        # Por ahora, devolvemos una lista de los destinos más vendidos
        from apps.bookings.models import SegmentoVuelo
        start_date = timezone.now() - timedelta(days=30 * months)
        
        top_cities = (
            SegmentoVuelo.objects.filter(fecha_salida__gte=start_date)
            .values('destino__nombre')
            .annotate(count=Count('id_segmento_vuelo'))
            .order_by('-count')[:5]
        )
        
        return [c['destino__nombre'] for c in top_cities if c['destino__nombre']]

    def generate_forecast(self) -> Dict[str, Any]:
        """
        Orquesta el análisis y la generación de la predicción con IA.
        """
        if not ai_engine.is_ready:
            return {"error": "IA no disponible para análisis."}

        # 1. Recolectar datos
        historical_sales = self.get_historical_data()
        top_destinations = self.get_top_destinations_historical()
        current_date = timezone.now().strftime("%Y-%m-%d")

        if not historical_sales:
            return {"error": "Datos insuficientes para realizar una predicción (mínimo 1 mes de ventas)."}

        # 2. Construir Prompt
        prompt = f"""
        Actúa como un Analista de Inteligencia de Negocios Senior especializado en el sector Turismo.
        
        CONTEXTO ACTUAL:
        Fecha de reporte: {current_date}
        
        DATOS HISTÓRICOS DE VENTAS (Últimos 12 meses):
        {historical_sales}
        
        DESTINOS CON MÁS TRACCIÓN RECIENTE:
        {top_destinations}
        
        TAREAS:
        1. Analiza los patrones de estacionalidad y el crecimiento mes a mes.
        2. Predice el volumen de ventas para el PRÓXIMO MES basándote en tendencias de la industria y datos locales.
        3. Identifica destinos que deberían ser promocionados (tendencias emergentes).
        4. Genera recomendaciones tácticas de marketing (ej: 'Vender paquetes de esquí por cercanía a temporada', 'Foco en B2B corporativo por reactivación post-vacacional').
        
        REQUISITOS:
        - Sé específico y métrico.
        - Las recomendaciones deben ser accionables para una Agencia de Viajes.
        - No menciones que eres una IA, actúa como el consultor experto.
        """

        try:
            forecast = ai_engine.call_gemini(
                prompt=prompt,
                response_schema=SalesForecastSchema
            )
            return forecast
        except Exception as e:
            logger.error(f"Error generando AI Forecast: {e}")
            return {"error": str(e)}

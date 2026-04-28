import logging
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from core.services.ai_engine import ai_engine
from core.models.ai_schemas import ResultadoParseoSchema

logger = logging.getLogger(__name__)

class AIParserService:
    """
    SaaS AI Parser Engine (Tier 2 Upgrade)
    Sustituye a los parsers basados en Regex con un modelo 100% probabilístico guiado.
    """
    
    SYSTEM_INSTRUCTION = """
    Eres el motor de extracción de datos de TravelHub. 
    Analizas boletos aéreos de GDS (Sabre, KIU, Amadeus) y devuelves exclusivamente JSON.
    
    REGLAS DE ORO:
    1. Si hay múltiples pasajeros, devuelve una lista en 'boletos'.
    2. Convierte todas las fechas a ISO (YYYY-MM-DD).
    3. Extrae CADA segmento de vuelo con su localizador de aerolínea si existe.
    4. Si un campo no existe, pon null, no inventes.
    5. No incluyas explicaciones, solo el objeto JSON validado.
    """

    @classmethod
    def parse_text(cls, raw_text: str) -> Dict[str, Any]:
        """
        Envía el texto crudo a Gemini y valida la respuesta.
        """
        logger.info(f"🤖 Preparando extracción de IA para bloque de texto ({len(raw_text)} chars)")
        
        try:
            # Limpieza básica para reducir ruido de tokens
            sanitized_text = raw_text.strip()[:10000] 
            
            response = ai_engine.call_gemini(
                prompt=f"Analiza este boleto y extrae los datos:\n\n{sanitized_text}",
                system_instruction=cls.SYSTEM_INSTRUCTION,
                response_schema=ResultadoParseoSchema
            )
            
            if "error" in response:
                logger.error(f"❌ Error en llamada a Gemini: {response['error']}")
                return response
                
            return response
            
        except Exception as e:
            logger.error(f"🔥 Fallo crítico en AIParserService: {str(e)}")
            return {"error": str(e)}

    @classmethod
    def get_destination_image(cls, destination: str) -> str:
        """
        Retorna una URL de imagen de Unsplash optimizada para el destino.
        """
        if not destination or destination.lower() in ["unknown", "tu próximo viaje"]:
            return "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?q=80&w=2021&auto=format&fit=crop"
        
        # Mapa de destinos comunes para evitar latencia de API (Seed Data)
        mapping = {
            "MADRID": "https://images.unsplash.com/photo-1539037116277-4db20889f2d4?q=80&w=2070",
            "CARACAS": "https://images.unsplash.com/photo-1583259833504-f5fe72714571?q=80&w=2074",
            "BOGOTA": "https://images.unsplash.com/photo-1536305030202-cc69ec992011?q=80&w=2070",
            "PARIS": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?q=80&w=2073",
            "MIAMI": "https://images.unsplash.com/photo-1506466010722-395aa2bef877?q=80&w=2070",
            "MEXICO": "https://images.unsplash.com/photo-1512813588911-721c97a5542b?q=80&w=2070"
        }
        
        dest_upper = str(destination).upper()
        for key, url in mapping.items():
            if key in dest_upper:
                return url
        
        # Fallback genérico de ciudad si no está en el mapa
        query = destination.replace(" ", "+")
        return f"https://source.unsplash.com/featured/?city,{query}"

    @classmethod
    def analyze_sales_opportunities(cls, data: Dict[str, Any]) -> List[str]:
        """
        Genera sugerencias de ventas basadas en el itinerario.
        """
        # Por ahora heurística simple, luego llamar a IA
        proposals = []
        vuelos = data.get("boletos", [{}])[0].get("itinerario", [])
        
        if vuelos:
            destino = vuelos[-1].get("destino", "su destino")
            proposals.append(f"Este viajero aún no tiene reserva de Hotel en {destino}.")
            proposals.append(f"Recomendar Seguro de Viaje para la ruta {vuelos[0]['origen']} - {destino}.")
            
        return proposals

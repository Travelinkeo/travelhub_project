from pydantic import BaseModel, Field
from typing import List, Optional

class FlightQuoteSegmentSchema(BaseModel):
    airline: str = Field(..., description="Nombre de la aerolínea")
    departureDate: str = Field(..., description="Fecha del vuelo (formato '20 Abr')")
    departureCode: str = Field(..., description="Código IATA de origen (3 letras, ej: CCS)")
    arrivalCode: str = Field(..., description="Código IATA de destino (3 letras, ej: MAD)")
    departureCity: str = Field(..., description="Nombre de la ciudad de origen (ej: Caracas)")
    arrivalCity: str = Field(..., description="Nombre de la ciudad de destino (ej: Madrid)")
    departureTime: str = Field(..., description="Hora de salida (formato 24h, ej: 14:30)")
    arrivalTime: str = Field(..., description="Hora de llegada (formato 24h, ej: 17:00)")
    stops: str = Field(..., description="Número de escalas o 'Directo'")
    baggage: str = Field("1 Maleta 23kg", description="Información de equipaje incluida")

class CotizacionMagicSchema(BaseModel):
    """
    Esquema para la extracción inteligente de cotizaciones rápidas GDS.
    """
    destination: str = Field(..., description="Ciudad de destino principal")
    destination_description: str = Field(..., description="Frase inspiradora sobre el destino")
    type: str = Field("Vuelo Redondo", description="Tipo de viaje (Solo Ida, Redondo, Multitrayecto)")
    outboundDate: str = Field(..., description="Fecha de salida estimada (ej: 15 Oct)")
    returnDate: Optional[str] = Field(None, description="Fecha de regreso estimada (si aplica)")
    totalPrice: float = Field(..., description="Precio total base extraído (sin markup)")
    currency: str = Field("USD", description="Moneda del precio extraído")
    flights: List[FlightQuoteSegmentSchema] = Field(..., description="Lista de segmentos de vuelo estructurados")
    image_search_query: str = Field(..., description="Término de búsqueda óptimo para una foto de Unsplash (ej: 'Madrid Cityscape')")
    notas_ia: Optional[str] = Field(None, description="Cualquier nota relevante sobre restricciones o clases")

from pydantic import BaseModel, Field
from typing import List, Optional

class TramoVueloSchema(BaseModel):
    aerolinea: str = Field(description="Código IATA o nombre de la aerolínea del tramo")
    numero_vuelo: Optional[str] = Field(description="Número de vuelo (ej: TK0224)")
    origen: str = Field(description="Ciudad o código IATA de origen")
    fecha_salida: str = Field(description="Fecha de salida (ej: 25FEB o 2025-02-25)")
    hora_salida: str = Field(description="Hora de salida (ej: 09:17 AM o 11:35)")
    destino: str = Field(description="Ciudad o código IATA de destino")
    hora_llegada: str = Field(description="Hora de llegada")
    cabina: Optional[str] = Field(description="Clase de cabina (Económica, Ejecutiva, etc.)")
    clase: Optional[str] = Field(description="Clase tarifaria (clase de reserva, ej: Y, M, L)")
    localizador_aerolinea: Optional[str] = Field(description="Localizador específico de la aerolínea si difiere del principal")
    equipaje: Optional[str] = Field(description="Franquicia de equipaje (ej: 2PC, 23KG)")

class BoletoAereoSchema(BaseModel):
    nombre_pasajero: str = Field(description="Nombre completo del pasajero (Formato GDS: APELLIDO/NOMBRE)")
    codigo_identificacion: Optional[str] = Field(description="FOID, DNI, Cédula o Pasaporte del pasajero")
    solo_nombre_pasajero: str = Field(description="Únicamente el primer nombre del pasajero (para saludos humanos)")
    numero_boleto: Optional[str] = Field(description="Número de boleto de 13 dígitos. Obligatorio si existe")
    fecha_emision: Optional[str] = Field(description="Fecha en la que se emitió el documento")
    agente_emisor: Optional[str] = Field(description="Código IATA o Identificador numérico/alfanumérico de la oficina/agente emisor")
    codigo_reserva: str = Field(description="Localizador principal de la reserva (PNR)")
    solo_codigo_reserva: str = Field(description="Localizador de 6 caracteres limpio (sin prefijos como C1/)")
    nombre_aerolinea: str = Field(description="Nombre de la aerolínea principal o validadora")
    direccion_aerolinea: Optional[str] = Field(description="Dirección física de la aerolínea (si está presente)")
    itinerario: List[TramoVueloSchema] = Field(description="Lista detallada de todos los tramos de vuelo del itinerario")
    tarifa: float = Field(description="Monto de la tarifa base/neta (valor numérico)")
    impuestos: float = Field(description="Monto total de todos los impuestos y tasas (valor numérico)")
    total: float = Field(description="Monto total pagado (Tarifa + Impuestos)")
    moneda: str = Field(description="Código de moneda (ej: USD, VES)", default="USD")
    source_system: str = Field(description="Sistema de origen detectado (KIU, SABRE, AMADEUS, WINGO, COPA_SPRK, etc.)")

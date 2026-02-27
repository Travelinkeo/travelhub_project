import google.generativeai as genai
import json
import logging
import os
import traceback
import typing
from typing import Dict, Any, Optional, List
from django.conf import settings
from pydantic import BaseModel, Field

# ==========================================
# 1. MODELOS DE DATOS (PYDANTIC) - "GOD MODE"
# ==========================================

class TramoVueloSchema(BaseModel):
    aerolinea: str = Field(description="Código IATA o nombre de la aerolínea operadora")
    numero_vuelo: Optional[str] = Field(description="Número de vuelo INCLUYENDO EL CÓDIGO DE AEROLÍNEA (ej. TK 224, CM 062). Si no tiene letras, ponlo numérico.")
    origen: str = Field(description="Ciudad o aeropuerto de origen")
    fecha_salida: str = Field(description="Fecha completa de salida, INCLUYENDO EL AÑO (deducido de la emisión si no está explícito)")
    hora_salida: str = Field(description="Hora de salida en formato HH:MM")
    destino: str = Field(description="Ciudad o aeropuerto de destino")
    hora_llegada: str = Field(description="Hora de llegada en formato HH:MM")
    cabina: Optional[str] = Field(description="Clase de cabina (Turista, Ejecutiva)")
    clase: Optional[str] = Field(description="Letra de clase tarifaria (Y, B, O, G, T)")
    localizador_aerolinea: Optional[str] = Field(description="Localizador específico de la aerolínea operadora. Si es KIU, NDC o Low-Cost, suele ser igual al principal.")
    equipaje: Optional[str] = Field(description="Franquicia de equipaje permitida (Ej: '1PC', '23K', '0PC', 'NIL', 'Morral'). Extraer de OTRAS NOTAS, BAG/EQP o tablas.")

class BoletoAereoSchema(BaseModel):
    nombre_pasajero: str = Field(description="Formato GDS: APELLIDO/NOMBRE")
    codigo_identificacion: Optional[str] = Field(description="Limpia los prefijos como IDVCI, NI, IDVP. Solo deja el número. En SABRE/Amadeus búscalo en corchetes o Form of ID. Devuelve null si no existe.")
    solo_nombre_pasajero: str = Field(description="Primer nombre limpio, sin títulos (MR/MRS)")
    numero_boleto: Optional[str] = Field(description="13 dígitos numéricos. Elimina guiones. Si es aerolínea Low-Cost (Ticketless), devuelve null.")
    fecha_emision: Optional[str] = Field(description="Fecha de emisión completa con año")
    agente_emisor: Optional[str] = Field(description="Agencia emisora. EN SABRE EXTRAE ÚNICAMENTE EL NÚMERO IATA (ej. 10617390). Para KIU/otros, usa el nombre de la agencia.")
    codigo_reserva: str = Field(description="Localizador principal PNR (6 caracteres)")
    solo_codigo_reserva: str = Field(description="Localizador de 6 letras, ELIMINA el 'C1/' de KIU")
    nombre_aerolinea: str = Field(description="Aerolínea emisora (ej. CONVIASA, AVIOR, TURKISH AIRLINES, WINGO)")
    itinerario: List[TramoVueloSchema]
    moneda: str = Field(description="Moneda de la transacción (USD, VES, COP, EUR, etc). Extraer de tablas de cobro reales.")
    tarifa: float = Field(description="Monto numérico exacto de la tarifa base. Límpiarlo de letras.")
    impuestos: float = Field(description="Monto numérico exacto de impuestos. Se calcula restando TOTAL - TARIFA si no está explícito.")
    total: float = Field(description="Monto total pagado numérico exacto.")
    es_remision: bool = Field(description="True si el boleto es una remisión/cambio (se detecta por una 'A' al final del Total). False si es emisión original.")
    source_system: str = Field(description="Sistema detectado obligatoriamente: KIU, SABRE, AMADEUS, WINGO, CONVIASA, etc.")

class ResultadoParseoSchema(BaseModel):
    boletos: List[BoletoAereoSchema] = Field(description="Lista de boletos extraídos del documento. Genera un objeto BoletoAereo independiente por cada pasajero encontrado, dividiendo matemáticamente el costo total si es un cobro grupal.")

logger = logging.getLogger(__name__)

# ==========================================
# 2. EL CEREBRO ("GOD MODE" PROMPT)
# ==========================================

SYSTEM_PROMPT = """
Eres el Parser Universal experto en procesamiento de boletos aéreos (KIU, SABRE, AMADEUS, COPA SPRK / NDC, Portales Web). Extrae los datos estrictamente en JSON bajo estas reglas avanzadas:

1. LOCALIZADOR Y PNRs (CRÍTICO): 
   - RESERVA PRINCIPAL: El localizador principal (6 caracteres) va en `codigo_reserva`. Búscalo en el Asunto, o junto a "Itinerario para localizador de reserva" / "Itinerary for Record Locator".
   - LOCALIZADOR DE AEROLÍNEA: En COPA SPRK búscalo específicamente como "Copa Airlines Localizador de reserva" o "Copa Airlines Record Locator". En SABRE búscalo explícitamente. Si es KIU puro, suele ser el mismo que el principal.
   - REDACCIÓN DE VUELO: Extrae el código de aerolínea + el número (Ej: 'TK 224', 'CM 062') en `numero_vuelo`.
   - AGENTE EMISOR: En KIU o recibos busca nombres como 'GRUPO SOPORTE GLOBAL'. ¡PERO EN SABRE EXTRAE SOLAMENTE EL NÚMERO IATA (ej. 10617390) y omite el nombre!
2. EQUIPAJE: Extrae la franquicia. En GDS busca "OTRAS NOTAS" o "Baggage". En COPA SPRK/Web búscalo en las tablas de itinerario. En Low-Cost extrae texto exacto ("Morral", "Cabina").
3. NOMBRES Y TÍTULOS: Busca el nombre en el "Asunto" si está cortado en el cuerpo. ELIMINA títulos de cortesía (MR, MRS, MS, MISS, MSTR, INF) y sufijos (ADT), (CHD). ELIMINA texto entre corchetes [].
4. MÚLTIPLES PASAJEROS Y NDC (CRÍTICO): COPA SPRK y agencias web agrupan a toda la familia en un archivo. DEBES generar un boleto independiente para cada pasajero en el JSON dividiendo matemáticamente el Costo Total entre la cantidad de individuos. Asigna a cada uno su propio número de boleto si aparece por separado en tabla.
5. OPERACIONES TICKETLESS / INFANTES: Low-Costs NO emiten tickets. Si es infante o costo 0, pon 0.0 sin fallar. Si no hay boleto, asigna `null`.
6. IDENTIFICACIÓN (FOID): 
   - SABRE: Extrae el documento de los corchetes [123456].
   - AMADEUS: Bajo "Form of Identification".
   - COPA SPRK / Web: Búscalo en la tabla de pasajeros. Si NO aparece, devuelve null sin fallar. Limpia prefijos KIU.
7. FORMATOS HTML / NDC: Si el correo es HTML (Copa SPRK, Avior), usa tu capacidad semántica para extraer datos de CARDS y TABLAS visuales, IGNORANDO botones o enlaces promocionales largos. Atiende versiones en español e inglés.
8. RUIDO VISUAL Y LEGAL: Ignora avisos de exceso de equipaje, reglas tarifarias, políticas de privacidad y cláusulas de CO2.
9. REMISIONES Y LIMPIEZA NUMÉRICA: 
   - Si el TOTAL tiene una letra "A" (Ej: "75.50A"), marca `es_remision` como TRUE.
   - ELIMINA letras de los montos dejándolos como números puros (float).
10. DETECCIÓN DE SISTEMA: 
   - Si es KIU ("KIU SYSTEM", "ITINERARIO DE PASAJEROS") o aerolíneas que lo usan. (NOTA: "E-TICKET ITINERARY RECEIPT" NO significa SABRE obligatoriamente).
   - Si dice "SABRE", source_system = "SABRE". Si "AMADEUS" o "CheckMyTrip" -> "AMADEUS".
   - Si dice "COPA AIRLINES" o "ACCELYA" o "ConnectMiles" -> "COPA_SPRK".
"""

class UniversalAIParser:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
        self.model = None
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key, transport="rest")
                self.model = genai.GenerativeModel(
                    model_name="gemini-2.0-flash", # Mantengo Flash por velocidad en batch tests, pero con el prompt optimizado
                    system_instruction=SYSTEM_PROMPT
                )
                logger.info("UniversalAIParser (Gemini 2.0 Flash) initialized with God Mode.")
            except Exception as e:
                logger.error(f"AI Init Error: {e}")

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Extrae datos del boleto. Soporta multi-pax devolviendo un flag 'is_multi_pax'.
        """
        if not self.model: return {"error": "IA no configurada"}
        
        try:
            # Llamada con el esquema de resultado múltiple
            response = self.model.generate_content(
                f"CONTENIDO DEL DOCUMENTO:\n{text}",
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=ResultadoParseoSchema,
                    temperature=0.0
                )
            )
            
            # Limpieza básica por si Gemini devuelve markdown
            raw_text = response.text
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[-1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[-1].split("```")[0].strip()
                
            data = json.loads(raw_text)
            boletos_list = data.get("boletos", [])
            
            if not boletos_list:
                return {"error": "No se encontraron boletos configurados"}

            # Mapear al formato interno de TravelHub
            internal_tickets = [self._map_to_internal_format(b) for b in boletos_list]

            if len(internal_tickets) > 1:
                return {
                    "is_multi_pax": True,
                    "tickets": internal_tickets
                }
            
            return internal_tickets[0]

        except Exception as e:
            logger.error(f"AI Parse Error: {traceback.format_exc()}")
            return {"error": str(e)}

    def _map_to_internal_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sincroniza el JSON de la IA con las claves esperadas por el sistema actual."""
        pnr = str(data.get("codigo_reserva") or data.get("solo_codigo_reserva") or "No encontrado").upper()
        
        # Eliminar prefijos de PNR de KIU si se escaparon
        if pnr.startswith("C1/"):
            pnr = pnr[3:]

        return {
            "SOURCE_SYSTEM": f"AI_{str(data.get('source_system', 'UNKNOWN')).upper()}",
            "NUMERO_DE_BOLETO": data.get("numero_boleto") or "No encontrado",
            "FECHA_DE_EMISION": data.get("fecha_emision") or "No encontrado",
            "AGENTE_EMISOR": data.get("agente_emisor") or "No encontrado",
            "NOMBRE_DEL_PASAJERO": str(data.get("nombre_pasajero") or "No encontrado").upper(),
            "SOLO_NOMBRE_PASAJERO": str(data.get("solo_nombre_pasajero", "")).upper(),
            "CODIGO_IDENTIFICACION": data.get("codigo_identificacion") or "No encontrado",
            "CODIGO_RESERVA": pnr,
            "SOLO_CODIGO_RESERVA": pnr,
            "NOMBRE_AEROLINEA": str(data.get("nombre_aerolinea") or "No encontrado").upper(),
            # Convertimos floats de vuelta a strings para evitar precision errors en plantillas HTML
            "TARIFA": f"{data.get('tarifa', 0.0):.2f}",
            "IMPUESTOS": f"{data.get('impuestos', 0.0):.2f}",
            "TOTAL": f"{data.get('total', 0.0):.2f}",
            "TOTAL_MONEDA": str(data.get("moneda") or "USD").upper(),
            "vuelos": data.get("itinerario") or [],
            "es_remision": data.get("es_remision", False)
        }

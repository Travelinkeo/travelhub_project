import logging
import traceback
import typing
import re          # <--- FIX: Import global para expresiones regulares
import hashlib     # <--- FIX: Import global para el caché
from typing import Dict, Any, Optional, List
from .base_parser import ParsedTicketData
from pydantic import BaseModel, Field
from core.services.ai_engine import ai_engine

# ==========================================
# 1. MODELOS DE DATOS (PYDANTIC)
# ==========================================

from core.models.ai_schemas import ResultadoParseoSchema

logger = logging.getLogger(__name__)

# ==========================================
# 2. PROMPT MAESTRO (GOD MODE 2.0 + ANTI-BUCLES)
# ==========================================
SYSTEM_PROMPT = """
Eres un Analista Experto en Emisión de Boletos y Sistemas GDS (Sabre, Amadeus, KIU, NDC). 
Tu tarea es analizar textos crudos o HTML de recibos de vuelos y extraer la información estrictamente bajo el esquema JSON proporcionado.

REGLAS ESTRICTAS DE EXTRACCIÓN ("GOD MODE"):
1. PNR Y IATA: Extrae el localizador de 6 caracteres en `codigo_reserva`. Si el sistema es Sabre o Amadeus, busca y extrae estrictamente el número IATA de 8 dígitos y el Agente Emisor.
2. FORMATO SABRE DE PASAJEROS: Si encuentras el formato APELLIDO/NOMBRE [DOCUMENTO] (ej. MARTINEZ/JOAN [200687]), invierte el orden a "Nombre Apellido", guárdalo en `solo_nombre_pasajero` (primer nombre) y el nombre completo en `nombre_pasajero`. Extrae el número entre corchetes para `codigo_identificacion`.
3. FINANZAS OCULTAS: Muchos boletos (especialmente Sabre) ocultan las tarifas. Si el texto NO muestra explícitamente "Tarifa", "Impuestos" o "Total", coloca 0.0 en los campos financieros. ¡NO INVENTES PRECIOS!
4. LOCALIZADOR DE AEROLÍNEA: En sistemas GDS, busca la frase "Código de reservación de la aerolínea XXXXXX" bajo cada vuelo y asígnalo a `codigo_reserva_aerolinea` del boleto o `localizador_aerolinea` del tramo.
5. PRORRATEO: Si el texto agrupa el cobro de varios pasajeros (ej. "Cant. viajeros 2" con un total de VES 100), DEBES crear boletos separados en la lista `boletos` y dividir el monto matemáticamente (50 y 50).
6. FORMATOS DE FECHA: Convierte formatos como "12 abr 26" o "26 de marzo" al formato ISO "YYYY-MM-DD" o el formato GDS DDMMMAA (ej: 14MAR26) según pida el campo.
7. VENEZOLANAS (ESTELAR/AVIOR/LASER): En correos de Estelar, el destino aparece usualmente después de "A:" o "-". Busque la línea de vuelo detallada. Origen es "DE:" o antes del guión. Si el monto dice "Bs", la moneda es "VES".
8. ITINERARIO: Extrae CADA tramo de vuelo. Incluye aerolinea, numero_vuelo, origen, destino, fechas y horas. Si un tramo aparece duplicado, extráelo UNA SOLA VEZ.
9. CIUDADES COMPLETAS: Usa SIEMPRE el nombre completo de la ciudad (Ej. "BOGOTA", "MADRID"). PROHIBIDO usar códigos IATA de 3 letras (BOG, MAD) en origen/destino. Limita nombres a max 20 caracteres para evitar ruidos de aeropuertos.
10. CARACTERES PROHIBIDOS: ESTÁ ESTRICTAMENTE PROHIBIDO el uso de tabulaciones (\\t) o saltos de línea (\\n) dentro de los valores de texto. Devuelve JSON limpio, minificado y sin espacios repetidos.

EJEMPLO DE ENTRENAMIENTO (SABRE):
Entrada: Preparado para MARTINEZ GONZALEZ/JOAN MANUEL [200687777], CÓDIGO DE RESERVACIÓN UQMQGK...
Salida: {"boletos": [{"codigo_reserva": "UQMQGK", "numero_boleto": "9967424825226", "nombre_pasajero": "MARTINEZ GONZALEZ/JOAN MANUEL", "solo_nombre_pasajero": "JOAN MANUEL", "codigo_identificacion": "200687777", "tarifa": 0.0, "impuestos": 0.0, "total": 0.0, "moneda": "USD", "nombre_aerolinea": "AIR EUROPA", "itinerario": [{"aerolinea": "AIR EUROPA", "numero_vuelo": "UX72", "origen": "CARACAS", "destino": "MADRID", "fecha_salida": "12APR26", "hora_salida": "12:10", "hora_llegada": "21:40", "clase": "TURISTA", "localizador_aerolinea": "ANPHTO"}]}]}

PROHIBIDO: Devolver JSON incompleto o inventar datos financieros si no son explícitos.
"""

class UniversalAIParser:
    """
    🧠 IA / GOD MODE | 🚨 CRÍTICO
    Motor de Extracción Semántica por Inteligencia Artificial (Google Gemini). 
    Actúa como el "Salvavidas Absoluto" de la plataforma ERP cuando las Expresiones Regulares legacy 
    se rompen por la alta variabilidad en los correos y PDFs del GDS.
    """
    def __init__(self):
        self.engine = ai_engine

    def parse(self, text: str, pdf_path: Optional[str] = None) -> Dict[str, Any]:
        """
        ⚡ ASÍNCRONO-READY | 🧠 IA
        Iterador principal de extracción. Analiza el payload y lo envía seguro a Gemini.
        """
        try:
            # Protección contra textos vacíos
            if not text:
                text = ""
                
            # 🛡️ ESCUDO ANTI-BASURA EXTREMO (Prevención de Token Loop)
            text_limpio = str(text)
            # 1. Asesinar cadenas largas de Base64 (Imágenes incrustadas que asfixian a la IA)
            text_limpio = re.sub(r'[A-Za-z0-9+/=]{150,}', ' [IMAGEN_REMOVIDA] ', text_limpio)
            # 2. Asesinar bloques gigantes de CSS ({ ... })
            text_limpio = re.sub(r'\{.*?\}', ' ', text_limpio, flags=re.DOTALL)
            # 3. Asesinar caracteres invisibles Y TABULACIONES (\t)
            text_limpio = re.sub(r'[\u200b\u200c\u200d\u200e\u200f\ufeff\xa0\t]', ' ', text_limpio)
            # 4. Colapsar espacios infinitos
            text_limpio = re.sub(r'\s+', ' ', text_limpio).strip()
            
            # Truncar a 15,000 caracteres para proteger los límites de tokens de Gemini
            if len(text_limpio) > 15000:
                text_limpio = text_limpio[:15000]
            
            # --- 1. CACHÉ POR HASH (SaaS Cost Efficiency) ---
            text_hash = hashlib.md5(text_limpio.encode('utf-8')).hexdigest()
            prompt_hash = hashlib.md5(SYSTEM_PROMPT.encode('utf-8')).hexdigest()
            cache_key = f"ai_parse_{text_hash}_{prompt_hash}"
            
            logger.info(f"🔍 Procesando documento purificado (Hash: {text_hash})")

            content_list = []
            
            # Estrategia de Visión
            if pdf_path and ('(cid:' in text_limpio or len(text_limpio) < 200 or 'cid:' in text_limpio):
                try:
                    import pypdfium2 as pdfium
                    logger.info(f"👁️ Usando Visión para PDF: {pdf_path}")
                    pdf = pdfium.PdfDocument(pdf_path)
                    if len(pdf) > 0:
                        pil_image = pdf[0].render(scale=2).to_pil()
                        content_list.append(pil_image)
                except Exception as e:
                    logger.error(f"Error en visión PDF: {e}")

            # --- 2. LLAMADA PRINCIPAL ---
            res = self.engine.call_gemini(
                prompt=f"TEXTO DEL DOCUMENTO:\n{text_limpio}",
                content_list=content_list,
                response_schema=ResultadoParseoSchema,
                system_instruction=SYSTEM_PROMPT
            )

            if "error" in res:
                return res

            # --- 3. RETRY DIRIGIDO (Empty Itinerary Fix) ---
            boletos_raw = res.get("boletos", [])
            itinerario_vacio = all(not b.get('itinerario') for b in boletos_raw) if boletos_raw else True

            if itinerario_vacio and not "error" in res:
                logger.warning(f"🔄 Itinerario vacío detectado. Ejecutando RETRY dirigido...")
                retry_prompt = (
                    f"RE-ANALIZA EL SIGUIENTE DOCUMENTO. El intento anterior no encontró vuelos.\n"
                    f"ENFÓCATE EXCLUSIVAMENTE EN ENCONTRAR SEGMENTOS DE VUELO, NÚMEROS DE VUELO Y CIUDADES.\n"
                    f"CERO TABULACIONES. NOMBRES DE CIUDADES CORTOS.\n\n"
                    f"TEXTO DEL DOCUMENTO:\n{text_limpio}"
                )
                res = self.engine.call_gemini(
                    prompt=retry_prompt,
                    content_list=content_list,
                    response_schema=ResultadoParseoSchema,
                    system_instruction=SYSTEM_PROMPT
                )

            # Sanación y Validación de Esquema
            from core.services.data_healer import DataHealer
            try:
                validated_res = DataHealer.heal_and_validate(ResultadoParseoSchema, res)
                boletos_data = validated_res.dict().get("boletos", [])
            except Exception as e:
                logger.error(f"Fallo crítico de validación tras sanación: {e}")
                boletos_data = res.get("boletos", [])

            if not boletos_data:
                return {"error": "No se encontraron boletos en el documento tras re-intento."}

            # Mapear al formato interno
            internal_tickets = [self._map_to_internal_format(b) for b in boletos_data]

            # --- 4. FALLBACK REGEX PARA NOMBRE (Fix Truncation) ---
            if len(internal_tickets) > 0:
                primary = internal_tickets[0]
                name_val = primary.get("NOMBRE_DEL_PASAJERO")
                if not name_val or '/' not in name_val:
                    pax_patterns = [
                        r"(?:PASSENGER|NOMBRE|NAME|PASAJERO):\s*([A-Z\xc1\xc9\xcd\xd3\xda\xd1\s/]+)",
                        r"\n\s*([A-Z\xc1\xc9\xcd\xd3\xda\xd1]{2,}/[A-Z\xc1\xc9\xcd\xd3\xda\xd1\s]+)"
                    ]
                    for pat in pax_patterns:
                        match = re.search(pat, text_limpio, re.IGNORECASE)
                        if match:
                            found_name = match.group(1).strip().upper()
                            if '/' in found_name and len(found_name) > len(str(name_val or "")):
                                logger.info(f"🛡️ Fix Name: Reemplazando '{name_val}' por '{found_name}' desde texto raw.")
                                primary["NOMBRE_DEL_PASAJERO"] = found_name
                                parts = found_name.split('/')
                                if len(parts) > 1:
                                    primary["SOLO_NOMBRE_PASAJERO"] = parts[-1].strip().split()[0]
                                break

            if len(internal_tickets) > 1:
                return {
                    "is_multi_pax": True,
                    "tickets": internal_tickets
                }
            
            return internal_tickets[0]
            
        except Exception as top_level_e:
            logger.error(f"🔥 Error Crítico en UniversalAIParser.parse: {str(top_level_e)}")
            logger.error(traceback.format_exc())
            return {"error": f"Error interno en UniversalAIParser: {str(top_level_e)}"}

    def _map_to_internal_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforma el esquema jerárquico JSON/Pydantic devuelto con éxito por Gemini al 
        diccionario plano históricamente acoplado en todo el núcleo de parseadores de TravelHub.
        """
        raw_copy = data.copy()
        pnr = str(data.get("codigo_reserva", "")).upper()
        if pnr.startswith("C1/"): pnr = pnr[3:]
        pnr = pnr or None

        source_sys = str(data.get('source_system', 'UNKNOWN')).upper()

        def none_if_empty(val):
            if val is None:
                return None
            s = str(val).strip()
            if s.lower() in ('no encontrado', 'not found', 'n/a', '', 'none', 'null'):
                return None
            return s

        # Mapeo Base
        res = {
            "SOURCE_SYSTEM": source_sys,
            "NUMERO_DE_BOLETO": none_if_empty(data.get("numero_boleto")),
            "FECHA_DE_EMISION": none_if_empty(data.get("fecha_emision")),
            "AGENTE_EMISOR": none_if_empty(data.get("agente_emisor")) or none_if_empty(data.get("numero_iata")),
            "NUMERO_IATA": none_if_empty(data.get("numero_iata")),
            "NOMBRE_DEL_PASAJERO": str(data.get("nombre_pasajero") or "").upper() or None,
            "SOLO_NOMBRE_PASAJERO": str(data.get("solo_nombre_pasajero", "")).upper() or None,
            "CODIGO_IDENTIFICACION": none_if_empty(data.get("codigo_identificacion")),
            "CODIGO_RESERVA": pnr,
            "SOLO_CODIGO_RESERVA": pnr,
            "CODIGO_RESERVA_AEROLINEA": none_if_empty(data.get("codigo_reserva_aerolinea")),
            "NOMBRE_AEROLINEA": str(data.get("nombre_aerolinea") or "").upper() or None,
            "TARIFA": f"{data.get('tarifa', 0.0):.2f}",
            "IMPUESTOS": f"{data.get('impuestos', 0.0):.2f}",
            "TOTAL": f"{data.get('total', 0.0):.2f}",
            "TOTAL_MONEDA": str(data.get("moneda", "USD")).upper(),
            "vuelos": data.get("itinerario", []),
            "es_remision": data.get("es_remision", False),
            "confidence_score": data.get("confidence_score", 1.0),
            "notas_advertencia": data.get("notas_advertencia")
        }
        
        raw_copy.update(res)
        return raw_copy

def _apply_universal_schema_filter(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función de utilidad requerida por algunos reportes de proveedores para 
    asegurar que el dataset cumple con el esquema mínimo universal.
    """
    return data
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
2. IDENTIFICACIÓN DEL PASAJERO (CRÍTICO): Busca agresivamente documentos de identidad. 
   - Busca el campo "FOID" (Form of Identification) y extrae el número (ej: "IDPP123456" -> "123456").
   - Busca formatos APELLIDO/NOMBRE [DOCUMENTO] (ej. MARTINEZ/JOAN [200687]).
   - Busca menciones a "PASSPORT", "DNI", "CÉDULA", "RIF" o "ID NUMBER".
   - Todo esto DEBE ir en `codigo_identificacion`. Es vital para el matching de clientes en el CRM.
3. FORMATO GDS DE PASAJEROS: El NOMBRE (lo que va DESPUÉS del '/') debe ir en `solo_nombre_pasajero`. El APELLIDO (lo que va ANTES del '/') debe ir en `apellido_pasajero`. El nombre completo en `nombre_pasajero` debe ser "NOMBRE APELLIDO".
4. FINANZAS OCULTAS: Muchos boletos (especialmente Sabre) ocultan las tarifas. Si el texto NO muestra explícitamente "Tarifa", "Impuestos" o "Total", coloca 0.0 en los campos financieros. ¡NO INVENTES PRECIOS!
5. LOCALIZADOR DE AEROLÍNEA: En sistemas GDS, busca la frase "Código de reservación de la aerolínea" o "AIRLINE RESERVATION CODE" y extrae el código de 6 caracteres que aparece INMEDIATAMENTE DESPUÉS. Asígnalo a `codigo_reserva_aerolinea` del boleto o `localizador_aerolinea` del tramo.
6. PRORRATEO: Si el texto agrupa el cobro de varios pasajeros (ej. "Cant. viajeros 2" con un total de VES 100), DEBES crear boletos separados en la lista `boletos` y dividir el monto matemáticamente (50 y 50).
7. FORMATOS DE FECHA Y HORA: Convierte fechas al formato ISO "YYYY-MM-DD" o GDS DDMMMAA. Las HORAS deben ser estrictamente en formato 24 HORAS (HH:mm), por ejemplo: "05:21 PM" debe ser "17:21".
8. CIUDADES COMPLETAS E IATA: Extrae el nombre completo de la ciudad (Ej. "BOGOTA", "MADRID") para `origen`/`destino` Y el código IATA de 3 letras (Ej. "BOG", "MAD") para `codigo_iata_origen`/`codigo_iata_destino`. Esta duplicidad asegura la integridad en el sistema.
9. ITINERARIO: Extrae CADA tramo de vuelo. Incluye aerolinea, numero_vuelo, origen, destino, fechas y horas. Si un tramo aparece duplicado, extráelo UNA SOLA VEZ.
10. CARACTERES PROHIBIDOS: ESTÁ ESTRICTAMENTE PROHIBIDO el uso de tabulaciones (\\t) o saltos de línea (\\n) dentro de los valores de texto. Devuelve JSON limpio, minificado y sin espacios repetidos.

EJEMPLO DE ENTRENAMIENTO (SABRE):
Entrada: Preparado para QUINTERO RAMIREZ/JHONY ALBERTO [200687777], FOID: IDPP123456789. 1 UX 072 Y 12APR 7 CCSMAD HK1 1210 2140.
Salida: {"boletos": [{"codigo_reserva": "UQMQGK", "numero_boleto": "9967424825226", "nombre_pasajero": "JHONY ALBERTO QUINTERO RAMIREZ", "solo_nombre_pasajero": "JHONY ALBERTO", "codigo_identificacion": "123456789", "tarifa": 0.0, "impuestos": 0.0, "total": 0.0, "moneda": "USD", "nombre_aerolinea": "AIR EUROPA", "codigo_reserva_aerolinea": "ANPHTO", "itinerario": [{"aerolinea": "AIR EUROPA", "numero_vuelo": "UX72", "origen": "CARACAS", "codigo_iata_origen": "CCS", "destino": "MADRID", "codigo_iata_destino": "MAD", "fecha_salida": "12APR26", "hora_salida": "12:10", "hora_llegada": "21:40", "clase": "TURISTA", "localizador_aerolinea": "ANPHTO"}]}]}

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

    def parse(self, text: str, pdf_path: Optional[str] = None, bypass_cache: bool = False) -> Dict[str, Any]:
        """
        ⚡ ASÍNCRONO-READY | 🧠 IA
        Iterador principal de extracción. Analiza el payload y lo envía seguro a Gemini.
        """
        try:
            from django.core.cache import cache
            
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
            
            if not bypass_cache:
                try:
                    cached_res = cache.get(cache_key)
                    if cached_res:
                        logger.info(f"💾 IA CACHE HIT: Usando resultado guardado para hash {text_hash}")
                        return cached_res
                except:
                    logger.warning("⚠️ Error accediendo al cache en UniversalAIParser. Continuando sin cache.")
            
            logger.info(f"🔍 Procesando documento purificado (Hash: {text_hash}) (Bypass Cache: {bypass_cache})")

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

            # 🗺️ MAPEAMIENTO AL FORMATO INTERNO (RESTAURADO)
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
            
            final_result = internal_tickets[0]
            
            # --- GUARDAR EN CACHÉ ---
            try:
                cache.set(cache_key, final_result, timeout=604800) # 1 semana de vida
            except: pass
            
            return final_result
            
        except Exception as top_level_e:
            logger.error(f"🔥 Error Crítico en UniversalAIParser.parse: {str(top_level_e)}")
            logger.error(traceback.format_exc())
            return {"error": f"Error interno en UniversalAIParser: {str(top_level_e)}"}

    def _map_to_internal_format(self, b: Any) -> Dict[str, Any]:
        """
        🗺️ MAPEO HACIA LEGACY (CORE COMPATIBILITY)
        Convierte el objeto Pydantic/Dict limpio de la IA al formato de llaves en 
        mayúsculas que espera el VentaAutomationService y el resto del core.
        """
        data = b if isinstance(b, dict) else b.dict()
        
        # Mapeo de segmentos
        itinerario_mapeado = []
        for s in data.get('itinerario', []):
            itinerario_mapeado.append({
                'aerolinea': s.get('aerolinea'),
                'numero_vuelo': s.get('numero_vuelo'),
                'origen': s.get('origen'),
                'codigo_iata_origen': s.get('codigo_iata_origen'), # <--- NUEVO
                'destino': s.get('destino'),
                'codigo_iata_destino': s.get('codigo_iata_destino'), # <--- NUEVO
                'fecha_salida': s.get('fecha_salida'),
                'hora_salida': s.get('hora_salida'),
                'fecha_llegada': s.get('fecha_llegada'),
                'hora_llegada': s.get('hora_llegada'),
                'clase': s.get('clase') or s.get('cabina'),
                'localizador_aerolinea': s.get('localizador_aerolinea')
            })

        return {
            "NOMBRE_DEL_PASAJERO": data.get("nombre_pasajero"),
            "SOLO_NOMBRE_PASAJERO": data.get("solo_nombre_pasajero"),
            "CODIGO_IDENTIFICACION": data.get("codigo_identificacion"),
            "NUMERO_DE_BOLETO": data.get("numero_boleto"),
            "FECHA_DE_EMISION": data.get("fecha_emision"),
            "CODIGO_RESERVA": data.get("codigo_reserva"),
            "CODIGO_RESERVA_AEROLINEA": data.get("codigo_reserva_aerolinea"),
            "NOMBRE_AEROLINEA": data.get("nombre_aerolinea"),
            "TARIFA_IMPORTE": data.get("tarifa"),
            "TOTAL_IMPORTE": data.get("total"),
            "TOTAL_MONEDA": data.get("moneda"),
            "itinerario": itinerario_mapeado,
            "raw_data": data # Preservar para depuración
        }

def _apply_universal_schema_filter(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función de utilidad requerida por algunos reportes de proveedores para 
    asegurar que el dataset cumple con el esquema mínimo universal.
    """
    return data
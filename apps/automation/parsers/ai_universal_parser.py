import hashlib  # <--- FIX: Import global para el caché
import logging
import re  # <--- FIX: Import global para expresiones regulares
import traceback
from typing import Any

from apps.automation.services.ai_engine import ai_engine

# ==========================================
# 1. MODELOS DE DATOS (PYDANTIC)
# ==========================================
from core.api import ResultadoParseoSchema

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
3. FORMATO GDS DE PASAJEROS: El campo `nombre_pasajero` debe ser estrictamente en formato GDS: `APELLIDO/NOMBRE` (ej: `ZULOAGA/JESUS` o `ZULOAGA GOMEZ/MARIO JAVIER`). El campo `solo_nombre_pasajero` debe contener únicamente el primer nombre limpio (ej: `JESUS` o `MARIO`).
4. FINANZAS OCULTAS: Muchos boletos (especialmente Sabre) ocultan las tarifas. Si el texto NO muestra explícitamente "Tarifa", "Impuestos" o "Total", coloca 0.0 en los campos financieros. ¡NO INVENTES PRECIOS!
5. LOCALIZADOR DE AEROLÍNEA: En sistemas GDS, busca la frase "Código de reservación de la aerolínea" o "AIRLINE RESERVATION CODE" y extrae el código de 6 caracteres que aparece INMEDIATAMENTE DESPUÉS. Asígnalo a `codigo_reserva_aerolinea` del boleto o `localizador_aerolinea` del tramo.
6. PRORRATEO: Si el texto agógrafo el cobro de varios pasajeros (ej. "Cant. viajeros 2" con un total de VES 100), DEBES crear boletos separados en la lista `boletos` y dividir el monto matemáticamente (50 y 50).
7. FORMATOS DE FECHA Y HORA: Convierte fechas al formato ISO "YYYY-MM-DD" o GDS DDMMMAA. Las HORAS deben ser estrictamente en formato 24 HORAS (HH:mm), por ejemplo: "05:21 PM" debe ser "17:21".
8. CIUDADES COMPLETAS E IATA: Extrae el nombre completo de la ciudad (Ej. "BOGOTA", "MADRID") para `origen`/`destino` Y el código IATA de 3 letras (Ej. "BOG", "MAD") para `codigo_iata_origen`/`codigo_iata_destino`. Esta duplicidad asegura la integridad en el sistema.
9. ITINERARIO: Extrae CADA tramo de vuelo. Incluye aerolinea, numero_vuelo, origen, destino, fechas y horas. Si un tramo aparece duplicado, extráelo UNA SOLA VEZ.
10. CARACTERES PROHIBIDOS: ESTÁ ESTRICTAMENTE PROHIBIDO el uso de tabulaciones (\\t) o saltos de línea (\\n) dentro de los valores de texto. Devuelve JSON limpio, minificado y sin espacios repetidos.
11. FALSOS POSITIVOS Y PALABRAS DE RUIDO (NOMBRES):
    - ¡JAMÁS extraigas reglas de la aerolínea, políticas de equipaje, tasas, o frases como "PASAJERO DESCONOCIDO" o "UNKNOWN" como nombre de pasajero!
    - Si el texto solo contiene un contacto (ej. "Contacto MARIO JAVIER ZULUAGA GOMEZ") pero no hay lista de pasajeros explícita, usa al contacto como pasajero en el formato GDS (`ZULUAGA GOMEZ/MARIO JAVIER`).
    - Si el nombre del pasajero contiene palabras como "FOID", "RIF", "C.I." o números adjuntos al final, elimínalos por completo antes de retornar el JSON.
12. FORMATO VERTICAL DE NOMBRES: Si el texto dice "Nombre\\nJESUS\\nApellido\\nZULOAGA", el nombre del pasajero es "ZULOAGA/JESUS". Siempre dale prioridad a nombres reales sobre textos genéricos.
13. NÚMERO DE VUELO EN BAJO COSTO (WINGO): Para aerolíneas de bajo costo (como Wingo) donde no se especifique explícitamente el número de vuelo en el texto (ej. solo dice "CCS MDE" o "Caracas Medellín"), genéralo usando el código IATA de la aerolínea ("P5") seguido de un número secuencial o default como "000" (ej. "P5000") para garantizar la correctitud del itinerario.

EJEMPLO DE ENTRENAMIENTO (SABRE):
Entrada: Preparado para QUINTERO RAMIREZ/JHONY ALBERTO [200687777], FOID: IDPP123456789. 1 UX 072 Y 12APR 7 CCSMAD HK1 1210 2140.
Salida: {"boletos": [{"codigo_reserva": "UQMQGK", "numero_boleto": "9967424825226", "nombre_pasajero": "QUINTERO RAMIREZ/JHONY ALBERTO", "solo_nombre_pasajero": "JHONY ALBERTO", "codigo_identificacion": "123456789", "tarifa": 0.0, "impuestos": 0.0, "total": 0.0, "moneda": "USD", "nombre_aerolinea": "AIR EUROPA", "codigo_reserva_aerolinea": "ANPHTO", "itinerario": [{"aerolinea": "AIR EUROPA", "numero_vuelo": "UX72", "origen": "CARACAS", "codigo_iata_origen": "CCS", "destino": "MADRID", "codigo_iata_destino": "MAD", "fecha_salida": "12APR26", "hora_salida": "12:10", "hora_llegada": "21:40", "clase": "TURISTA", "localizador_aerolinea": "ANPHTO"}]}]}

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

    def parse(
        self, text: str, pdf_path: str | None = None, bypass_cache: bool = False
    ) -> dict[str, Any]:
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
            text_limpio = re.sub(r"[A-Za-z0-9+/=]{150,}", " [IMAGEN_REMOVIDA] ", text_limpio)
            # 2. Asesinar bloques gigantes de CSS ({ ... })
            text_limpio = re.sub(r"\{.*?\}", " ", text_limpio, flags=re.DOTALL)
            # 3. Asesinar caracteres invisibles Y TABULACIONES (\t)
            text_limpio = re.sub(r"[\u200b\u200c\u200d\u200e\u200f\ufeff\xa0\t]", " ", text_limpio)
            # 4. Colapsar espacios infinitos
            text_limpio = re.sub(r"\s+", " ", text_limpio).strip()

            # Truncar a 15,000 caracteres para proteger los límites de tokens de Gemini
            if len(text_limpio) > 15000:
                text_limpio = text_limpio[:15000]

            # --- 1. CACHÉ POR HASH (SaaS Cost Efficiency) ---
            text_hash = hashlib.sha256(text_limpio.encode("utf-8")).hexdigest()[:32]
            prompt_hash = hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()[:32]
            cache_key = f"ai_parse_{text_hash}_{prompt_hash}"

            if not bypass_cache:
                try:
                    cached_res = cache.get(cache_key)
                    if cached_res:
                        logger.info(
                            f"💾 IA CACHE HIT: Usando resultado guardado para hash {text_hash}"
                        )
                        return cached_res
                except Exception:
                    logger.warning(
                        "⚠️ Error accediendo al cache en UniversalAIParser. Continuando sin cache."
                    )

            logger.info(
                f"🔍 Procesando documento purificado (Hash: {text_hash}) (Bypass Cache: {bypass_cache})"
            )

            content_list = []

            if pdf_path and (
                "(cid:" in text_limpio or len(text_limpio) < 200 or "cid:" in text_limpio
            ):
                try:
                    import fitz
                    from PIL import Image

                    logger.info(f"👁️ Usando Visión para PDF: {pdf_path}")
                    with fitz.open(pdf_path) as pdf:
                        if len(pdf) > 0:
                            pix = pdf[0].get_pixmap(matrix=fitz.Matrix(2, 2))
                            pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            content_list.append(pil_image)
                except Exception as e:
                    logger.error(f"Error en visión PDF: {e}")

            # --- 2. LLAMADA PRINCIPAL CON FAIL-FAST ---
            import time

            from celery.exceptions import SoftTimeLimitExceeded

            start_ia = time.time()
            logger.info(">>> LLAMANDO A GEMINI...")

            try:
                res = self.engine.call_gemini(
                    prompt=f"TEXTO DEL DOCUMENTO:\n{text_limpio}",
                    content_list=content_list,
                    response_schema=ResultadoParseoSchema,
                    system_instruction=SYSTEM_PROMPT,
                )
                logger.info(f"<<< GEMINI RESPONDIÓ EN {time.time() - start_ia:.2f} SEGUNDOS")

            except SoftTimeLimitExceeded:
                logger.error(
                    "❌ TIMEOUT IA (SoftTimeLimit): Gemini no respondió a tiempo y Celery abortó la ejecución."
                )
                return {
                    "error": "API_FAILURE: TIMEOUT IA",
                    "requires_manual_review": True,
                    "fallback_triggered": True,
                    "status_detail": "Timeout IA: Ejecutando Fallback",
                }
            except Exception as e_api:
                # 🚨 FALLO CRÍTICO DE API (Timeout, 500, Rate Limit)
                logger.error(f"❌ Gemini API Failure (Switching to Fallback): {str(e_api)}")
                return {
                    "error": f"API_FAILURE: {str(e_api)}",
                    "requires_manual_review": True,
                    "fallback_triggered": True,
                    "status_detail": "Parseo Inteligente falló y requiere revisión manual",
                }

            # Helper para convertir a diccionario de forma segura (soporta Pydantic v1 y v2)
            def get_dict(obj):
                if hasattr(obj, "model_dump"):
                    return obj.model_dump()
                elif hasattr(obj, "dict"):
                    return obj.dict()
                return obj if isinstance(obj, dict) else {}

            res_dict = get_dict(res)

            if res_dict and "error" in res_dict:
                logger.warning(f"⚠️ Gemini returned logic error: {res_dict.get('error')}")
                res_dict["requires_manual_review"] = True
                res_dict["status_detail"] = "Parseo Inteligente falló y requiere revisión manual"
                return res_dict

            # --- 3. RETRY DIRIGIDO (Empty Itinerary Fix) ---
            boletos_raw = res_dict.get("boletos", [])
            itinerario_vacio = (
                all(not b.get("itinerario") for b in boletos_raw) if boletos_raw else True
            )

            if itinerario_vacio and "error" not in res_dict:
                logger.warning("🔄 Itinerario vacío detectado. Ejecutando RETRY dirigido...")
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
                    system_instruction=SYSTEM_PROMPT,
                )
                res_dict = get_dict(res)

            # Sanación y Validación de Esquema
            from apps.common.services.data_healer import DataHealer

            try:
                validated_res = DataHealer.heal_and_validate(ResultadoParseoSchema, res_dict)
                boletos_data = validated_res.dict().get("boletos", [])
            except Exception as e:
                logger.error(f"Fallo crítico de validación tras sanación: {e}")
                boletos_data = res_dict.get("boletos", [])

            if not boletos_data:
                return {"error": "No se encontraron boletos en el documento tras re-intento."}

            # 🗺️ MAPEAMIENTO AL FORMATO INTERNO (RESTAURADO)
            internal_tickets = [self._map_to_internal_format(b) for b in boletos_data]

            # --- 4. FALLBACK REGEX PARA NOMBRE (Fix Truncation) ---
            if len(internal_tickets) > 0:
                primary = internal_tickets[0]
                name_val = primary.get("NOMBRE_DEL_PASAJERO")
                if not name_val or "/" not in name_val:
                    pax_patterns = [
                        r"(?:PASSENGER|NOMBRE|NAME|PASAJERO):\s*([A-Z\xc1\xc9\xcd\xd3\xda\xd1\s/]+)",
                        r"\n\s*([A-Z\xc1\xc9\xcd\xd3\xda\xd1]{2,}/[A-Z\xc1\xc9\xcd\xd3\xda\xd1\s]+)",
                    ]
                    for pat in pax_patterns:
                        match = re.search(pat, text_limpio, re.IGNORECASE)
                        if match:
                            found_name = match.group(1).strip().upper()
                            # Clean stop keywords
                            stop_keywords = [
                                "NÚMERO DE",
                                "NUMERO DE",
                                "TIQUETE",
                                "TICKET",
                                "EMAIL",
                                "CORREO",
                                "TELÉFONO",
                                "TELEFONO",
                                "NOMBRE DE",
                                "PASSENGER",
                                "DOCUMENTO",
                                "DETALLES",
                                "ORIGEN",
                                "SALIDA",
                                "LLEGADA",
                                "VUELO",
                                "FOID",
                                "RIF",
                                "C.I.",
                                "IDENTIFICACION",
                                "IDENTIFICACIÓN",
                                "PASAJERO DESCONOCIDO",
                                "UNKNOWN",
                            ]
                            for kw in stop_keywords:
                                if kw in found_name:
                                    found_name = found_name.split(kw)[0].strip()
                            found_name = re.sub(
                                r"[^A-Z\xc1\xc9\xcd\xd3\xda\xd1\s/]+$", "", found_name
                            ).strip()

                            if "/" in found_name and len(found_name) > len(str(name_val or "")):
                                logger.info(
                                    f"🛡️ Fix Name: Reemplazando '{name_val}' por '{found_name}' desde texto raw."
                                )
                                primary["NOMBRE_DEL_PASAJERO"] = found_name
                                parts = found_name.split("/")
                                if len(parts) > 1:
                                    primary["SOLO_NOMBRE_PASAJERO"] = parts[-1].strip().split()[0]
                                break

            if len(internal_tickets) > 1:
                return {"is_multi_pax": True, "tickets": internal_tickets}

            final_result = internal_tickets[0]

            # --- GUARDAR EN CACHÉ ---
            try:
                cache.set(cache_key, final_result, timeout=604800)  # 1 semana de vida
            except Exception as e:
                logger.warning(f"Error guardando en cache: {e}. Continuando sin cache.")

            return final_result

        except Exception as top_level_e:
            logger.error(f"🔥 Error Crítico en UniversalAIParser.parse: {str(top_level_e)}")
            logger.error(traceback.format_exc())
            return {"error": f"Error interno en UniversalAIParser: {str(top_level_e)}"}

    def _map_to_internal_format(self, b: Any) -> dict[str, Any]:
        """
        🗺️ MAPEO HACIA LEGACY (CORE COMPATIBILITY)
        Convierte el objeto Pydantic/Dict limpio de la IA al formato de llaves en
        mayúsculas que espera el VentaAutomationService y el resto del core.
        """
        data = b if isinstance(b, dict) else b.dict()

        # Mapeo de segmentos
        itinerario_mapeado = []
        for s in data.get("itinerario", []):
            itinerario_mapeado.append(
                {
                    "aerolinea": s.get("aerolinea"),
                    "numero_vuelo": s.get("numero_vuelo"),
                    "origen": s.get("origen"),
                    "codigo_iata_origen": s.get("codigo_iata_origen"),  # <--- NUEVO
                    "destino": s.get("destino"),
                    "codigo_iata_destino": s.get("codigo_iata_destino"),  # <--- NUEVO
                    "fecha_salida": s.get("fecha_salida"),
                    "hora_salida": s.get("hora_salida"),
                    "fecha_llegada": s.get("fecha_llegada"),
                    "hora_llegada": s.get("hora_llegada"),
                    "clase": s.get("clase") or s.get("cabina"),
                    "localizador_aerolinea": s.get("localizador_aerolinea"),
                }
            )

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
            "raw_data": data,  # Preservar para depuración
        }


def _apply_universal_schema_filter(data: dict[str, Any]) -> dict[str, Any]:
    """
    Función de utilidad requerida por algunos reportes de proveedores para
    asegurar que el dataset cumple con el esquema mínimo universal.
    """
    return data

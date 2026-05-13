import json
import logging
import os
import traceback
from typing import Any

from django.conf import settings
from google import genai
from google.genai import types
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class CircuitBreakerException(Exception):
    pass

class QuotaExhaustedException(Exception):
    """Lanzada cuando la cuota de la API de IA se ha agotado (Error 429)."""
    pass

class GeminiConfigurationError(RuntimeError):
    """Se lanza cuando la clave de API de Gemini no esta configurada."""

class AIEngine:
    """
    Motor centralizado de Inteligencia Artificial para TravelHub.
    Gestiona la configuración, modelos y llamadas estructuradas a Gemini.
    """
    
    DEFAULT_MODEL = "gemini-flash-latest"
    # El modelo Pro es mejor para razonamiento complejo
    PRO_MODEL = "gemini-pro-latest"
    VISION_MODEL = "gemini-flash-latest"
    FALLBACK_MODEL = "gemini-1.5-flash-8b"

    @classmethod
    def _ensure_configured(cls):
        """Asegura que el cliente genai esté configurado (lazy skip import overhead)"""
        if not hasattr(cls, '_client') or cls._client is None:
            api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
            if api_key:
                try:
                    # Configuración de timeout para evitar cuelgues en workers
                    http_options = types.HttpOptions(timeout=30000) # 30 segundos
                    cls._client = genai.Client(api_key=api_key, http_options=http_options)
                    cls._is_global_configured = True
                    logger.info("AIEngine: genai client configured lazily with 30s timeout.")
                except Exception as e:
                    logger.error(f"AIEngine: Lazy Config Error: {e}")
                    cls._is_global_configured = False
            else:
                logger.warning("AIEngine: No API Key found for lazy config.")
                cls._is_global_configured = False
        return cls._is_global_configured

    def __init__(self):
        # El constructor es ahora extremadamente ligero
        self.is_ready = False # Se evaluará en tiempo de ejecución

    def call_gemini(
        self, 
        prompt: str, 
        content_list: list[Any] | None = None, 
        response_schema: type[BaseModel] | None = None,
        model_name: str | None = None,
        temperature: float = 0.1,
        system_instruction: str | None = None,
        feature: str = "generic"
    ) -> dict[str, Any]:
        """
        Llamada unificada a Gemini (Protegida por Circuit Breaker nativo de Django).
        feature: Indica qué funcionalidad está usando la IA (para tracking de costos).
        """
        from django.core.cache import cache
        self._ensure_configured()
        
        # 1. Comprobar si el circuito está abierto (Gemini está caído)
        try:
            if cache.get('gemini_circuit_open'):
                logger.critical("🛑 CIRCUIT BREAKER ACTIVO: Gemini API está inalcanzable. Abortando request para proteger workers.")
                raise CircuitBreakerException("Servicio de IA temporalmente degradado.")
        except Exception as e_cache:
            logger.warning(f"⚠️ Error accediendo al cache (Redis): {e_cache}. Continuando sin cache.")
            
        try:
            # 2. Intentar llamar a la IA
            from apps.common.services.circuit_breaker import ai_circuit_breaker
            response = ai_circuit_breaker.call(
                self._execute_call_gemini,
                prompt, content_list, response_schema, model_name, temperature, system_instruction, feature
            )
            # Si tiene éxito, reseteamos el contador de fallos
            try:
                cache.delete('gemini_fail_count')
            except Exception as e_cache_del:
                logger.warning(f"No se pudo limpiar contador de fallos de Gemini en cache: {e_cache_del}")
            return response
            
        except Exception as e:
            # 3. Si falla, sumamos 1 al contador
            try:
                fails = cache.get('gemini_fail_count', 0) + 1
                cache.set('gemini_fail_count', fails, timeout=600) # Expira en 10 min
                
                # 4. Si llegamos a 5 fallos seguidos, ABRIMOS el circuito por 5 minutos
                if fails >= 5:
                    logger.critical("💥 5 Fallos consecutivos. APAGANDO conexión a Gemini por 5 minutos.")
                    cache.set('gemini_circuit_open', True, timeout=300) # 5 minutos de bloqueo
            except Exception:
                fails = "N/A"
            
            logger.warning(f"⚠️ Fallo en Gemini API (Intento {fails}/5): {str(e)}")
            
            # 5. INTENTO DE RESCATE: Si es un error de cuota (429), intentar con el modelo de respaldo
            if "429" in str(e) and model_name != self.FALLBACK_MODEL:
                logger.info(f"🔄 Cuota agotada en {model_name or self.DEFAULT_MODEL}. Reintentando con {self.FALLBACK_MODEL}...")
                return self.call_gemini(
                    prompt=prompt,
                    content_list=content_list,
                    response_schema=response_schema,
                    model_name=self.FALLBACK_MODEL,
                    temperature=temperature,
                    system_instruction=system_instruction,
                    feature=feature
                )

            # 6. ÚLTIMO RECURSO: Intentar sin esquema si el 404 persiste (problemas de habilitación/versión)
            if "404" in str(e) and response_schema:
                logger.warning("🔄 Error 404 en modo esquema. Reintentando en modo texto plano...")
                return self.call_gemini(
                    prompt=prompt,
                    content_list=content_list,
                    response_schema=None,
                    model_name=model_name,
                    temperature=temperature,
                    system_instruction=system_instruction,
                    feature=feature
                )
            
            raise e

    def analyze_gds_terminal(self, raw_text: str, gds_type: str = 'SABRE') -> dict[str, Any]:
        """
        Analiza texto crudo de terminales GDS (Sabre, KIU, Amadeus) y devuelve
        un JSON estructurado usando ResultadoParseoSchema.
        """
        from core.models.ai_schemas import ResultadoParseoSchema
        
        system_prompt = (
            f"Eres el motor de inteligencia Obsidian GDS AI de TravelHub. El sistema detectado es {gds_type}. "
            "Tu tarea es analizar capturas de pantalla o texto de terminales GDS (SABRE, AMADEUS, KIU) "
            "y extraer la información de reserva de forma ultra-precisa.\n\n"
            "REGLAS CRÍTICAS:\n"
            f"1. Estás analizando un formato de {gds_type}.\n"
            "2. Extrae todos los pasajeros y sus documentos (DOCS/FOID) si están presentes.\n"
            "   REGLA SABRE/KIU: El número de documento, pasaporte o ID del pasajero siempre se encuentra inmediatamente después del símbolo asterisco (*) pegado al nombre o etiqueta FOID. "
            "3. Extrae el itinerario completo (vuelos, fechas, rutas).\n"
            "   - NOTA PARA SABRE: Los aeropuertos suelen estar pegados (ej: CCSIST). DEBES SEPARARLOS: Origen 'CCS', Destino 'IST'.\n"
            "4. Extrae la tarifa base, impuestos y total.\n"
            "5. CAMPOS OBLIGATORIOS por segmento: 'origen_ciudad' y 'destino_ciudad' (nombre completo, ej: 'Madrid', 'Bogotá'), además de los códigos IATA.\n"
            "6. Si no hay año en las fechas, asume el año actual o el próximo basado en el contexto.\n"
            "7. Devuelve un objeto JSON que cumpla estrictamente con el esquema ResultadoParseoSchema."
        )
        
        raw_response = self.call_gemini(
            prompt=f"Analiza este texto de terminal GDS:\n\n{raw_text}",
            system_instruction=system_prompt,
            response_schema=ResultadoParseoSchema,
            feature="gds_parsing"
        )
        
        # Devolvemos el schema completo (con la lista 'boletos') para el Analyzer
        return raw_response

    def parse_structured_data(
        self, 
        text: str, 
        schema: type[BaseModel], 
        system_prompt: str | None = None,
        images: list[Any] | None = None
    ) -> dict[str, Any]:
        """
        Extrae datos estructurados de un texto (e imágenes opcionales) 
        basándose en un esquema de Pydantic.
        """
        return self.call_gemini(
            prompt=text,
            content_list=images,
            response_schema=schema,
            system_instruction=system_prompt
        )

    def _execute_call_gemini(
        self, 
        prompt: str, 
        content_list: list[Any] | None = None, 
        response_schema: type[BaseModel] | None = None,
        model_name: str | None = None,
        temperature: float = 0.1,
        system_instruction: str | None = None,
        feature: str = "generic"
    ) -> dict[str, Any]:
        """
        Ejecución real de la llamada (Privada para el Circuit Breaker).
        """
        if not self._ensure_configured():
            return {"error": "IA no configurada (falta API Key)"}

        try:
            # Si hay contenido multimedia, usamos el modelo de visión
            is_media = self._has_media(content_list)
            selected_model = model_name or (self.VISION_MODEL if is_media else self.DEFAULT_MODEL)

            # Preparar inputs
            contents = []
            if content_list:
                for item in content_list:
                    if isinstance(item, dict | list):
                        contents.append(item)
                    else:
                        contents.append(str(item))
            
            if prompt:
                contents.append(prompt)

            # Generación estructurada si hay schema
            try:
                config = types.GenerateContentConfig(
                    temperature=temperature,
                )
                if system_instruction:
                    config.system_instruction = system_instruction
                if response_schema:
                    config.response_mime_type = "application/json"
                    config.response_schema = response_schema
                else:
                    config.response_mime_type = "text/plain"

                response = self._client.models.generate_content(
                    model=selected_model,
                    contents=contents,
                    config=config
                )
                self._log_usage(None, selected_model, feature, 0, 0, "SUCCESS")
            except Exception as e:
                error_str = str(e)
                if "429" in error_str and selected_model != self.FALLBACK_MODEL:
                    logger.info(f"🔄 Cuota agotada en {selected_model}. Reintentando con {self.FALLBACK_MODEL}...")
                    return self._execute_call_gemini(prompt, content_list, response_schema, self.FALLBACK_MODEL, temperature, system_instruction)
                
                if "404" in error_str or "API has not been used" in error_str:
                    logger.error(f"❌ API DESHABILITADA o MODELO NO ENCONTRADO: {error_str}")
                    return {"error": f"La API de Gemini o el modelo {selected_model} no están disponibles."}

                if response_schema:
                    config_fallback = types.GenerateContentConfig(
                        temperature=temperature,
                        response_mime_type="application/json"
                    )
                    if system_instruction:
                        config_fallback.system_instruction = system_instruction
                    response = self._client.models.generate_content(
                        model=selected_model,
                        contents=contents,
                        config=config_fallback
                    )
                    self._log_usage(None, selected_model, feature, 0, 0, "SUCCESS_WITHOUT_SCHEMA")
                else:
                    raise e

            raw_text = response.text
            
            if response_schema:
                try:
                    cleaned_json = self._clean_json_response(raw_text)
                    return json.loads(cleaned_json)
                except Exception as parse_err:
                    # 🛡️ Audit Step 3.1: Robustez de IA - Logging detallado en fallo
                    logger.error("❌ [AIEngine] Error crítico parseando JSON de IA.")
                    logger.error(f"Error detallado: {parse_err}")
                    # Grabamos el output completo en un archivo temporal para análisis si es muy grande
                    logger.error(f"RAW OUTPUT (Preview): {raw_text[:500]}...")
                    
                    # Intentamos una extracción secundaria más agresiva
                    try:
                        second_chance = self._extract_json_aggressive(raw_text)
                        if second_chance:
                            return json.loads(second_chance)
                    except Exception as e_agg:
                        logger.warning(f"Extraccion JSON agresiva tambien fallo: {e_agg}")
                    
                    return {
                        "error": f"Error de formato en la respuesta de IA: {str(parse_err)}",
                        "status": "PARSE_ERROR",
                        "raw_output": raw_text # Incluimos el raw en el dict para que el llamador decida
                    }
            
            return {"text": raw_text}

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "Resource exhausted" in error_str:
                logger.error(f"🚨 CUOTA AGOTADA en Gemini: {error_str}")
                raise QuotaExhaustedException("La cuota de la API de IA se ha agotado.") from e
                
            self._log_usage(None, selected_model, feature, 0, 0, f"FAILED: {error_str[:20]}")
            logger.error(f"AIEngine Call Error: {traceback.format_exc()}")
            return {"error": str(e)}

    def _clean_json_response(self, text: str) -> str:
        """
        Limpia la respuesta de la IA de forma robusta.
        Elimina marcadores markdown, comentarios de estilo JS y busca el bloque JSON.
        """
        if not text:
            return "{}"
        
        import re
        
        # 1. Eliminar marcadores markdown y texto circundante obvio
        text = re.sub(r'```(?:json)?', '', text)
        text = text.replace('```', '')
        
        # 2. Eliminar comentarios de una línea (// ...) que a veces la IA incluye
        # Solo si no están dentro de strings (esto es una aproximación simple)
        text = re.sub(r'^\s*//.*$', '', text, flags=re.MULTILINE)
        
        # 3. Buscar el bloque JSON más externo (greedy match)
        # Intentamos encontrar el primer '{' y el último '}'
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1:
            candidate = text[start:end+1]
            # Limpieza de caracteres de control e invisibles
            candidate = candidate.replace('\u200b', '').replace('\ufeff', '')
            return candidate.strip()
            
        # Si no hay llaves, probamos con corchetes (arrays)
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1:
            return text[start:end+1].strip()
            
        return text.strip()

    def _extract_json_aggressive(self, text: str) -> str | None:
        """
        Intento secundario de extracción usando Regex más agresiva para limpiar basura al final.
        """
        import re
        # Busca el bloque que empieza por { y termina por } ignorando lo que haya fuera
        # El patrón [^{]* y [^}]* ayuda a ser un poco más selectivo si hay múltiples bloques,
        # pero para Gemini el greedy suele ser mejor para capturar el objeto raíz.
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            # Limpiar posibles comas finales antes de cerrar llaves/corchetes (un error común de IA)
            content = match.group(1)
            content = re.sub(r',\s*([\}\]])', r'\1', content)
            return content
        return None

    def _has_media(self, content_list: list[Any] | None) -> bool:
        if not content_list:
            return False
        for item in content_list:
            if isinstance(item, dict) and "mime_type" in item:
                return True
            if hasattr(item, 'format') or "Image" in str(type(item)):
                return True
        return False

    def _log_usage(self, agencia, model_name, feature, input_tokens, output_tokens, status):
        """
        Registra el uso de la IA en la base de datos de forma segura.
        """
        try:
            from core.middleware import get_current_agency
            from core.models.ai import AIUsageLog
            
            target_agencia = agencia or get_current_agency()
            
            # Estimación simple de costos (Referencial)
            cost = 0
            if "pro" in model_name:
                cost = 0.01
            elif "flash" in model_name:
                cost = 0.001
            
            AIUsageLog.objects.create(
                agencia=target_agencia,
                model_name=model_name,
                feature=feature,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost=cost,
                status=status
            )
        except Exception as e:
            logger.error(f"Error logging AI usage: {e}")

# Instancia singleton
ai_engine = AIEngine()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')


def generate_content(prompt: str, model_name: str = "gemini-2.0-flash") -> str:
    """Wrapper de compatibilidad (antes en gemini.py). Delega en AIEngine."""
    try:
        return ai_engine.call_gemini(prompt, model_name=model_name)
    except GeminiConfigurationError:
        raise
    except Exception:
        return ""


def generate_text_from_prompt(prompt: str, model_name: str = "gemini-2.0-flash-lite-001") -> str:
    """Wrapper de compatibilidad (antes en gemini_client.py). Delega en AIEngine."""
    try:
        return ai_engine.call_gemini(prompt, model_name=model_name)
    except Exception:
        return "Error al contactar la API de Gemini"


def generate_structured_data(prompt: str, model_name: str = "gemini-2.0-flash-lite-001") -> str:
    """Envía un prompt a Gemini y fuerza respuesta en formato JSON."""
    try:
        result = ai_engine.call_gemini(prompt, model_name=model_name)
        if isinstance(result, dict):
            return json.dumps(result)
        return result or "{}"
    except Exception:
        return "{}"


def analizar_documento_con_gemini_estructurado(
    file_bytes: bytes,
    mime_type: str,
    prompt_text: str,
    response_schema: type,
) -> dict:
    """Analiza un documento (PDF/imagen) con Gemini Vision y retorna dict."""
    from google.genai import types as genai_types

    api_key = getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiConfigurationError("GEMINI_API_KEY no configurada en settings.")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            genai_types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            prompt_text,
        ],
        config=genai_types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=response_schema,
        ),
    )
    try:
        return json.loads(response.text)
    except Exception as e:
        raise ValueError(
            f"Gemini no devolvio un JSON valido. Respuesta: {getattr(response, 'text', '')}"
        ) from e


def list_available_models():
    """Lista los modelos disponibles en la cuenta Gemini."""
    api_key = getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: No se proporciono API Key."
    try:
        client = genai.Client(api_key=api_key)
        return [m.name for m in client.models.list()]
    except Exception as e:
        logger.error(f"Error al listar modelos: {e}")
        return f"Error: {e}"

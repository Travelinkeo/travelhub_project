import os
import json
import logging
import traceback
from typing import Dict, Any, Optional, List, Type, Union
from django.conf import settings
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class CircuitBreakerException(Exception):
    pass

class QuotaExhaustedException(Exception):
    """Lanzada cuando la cuota de la API de IA se ha agotado (Error 429)."""
    pass

class AIEngine:
    """
    Motor centralizado de Inteligencia Artificial para TravelHub.
    Gestiona la configuración, modelos y llamadas estructuradas a Gemini.
    """
    
    DEFAULT_MODEL = "gemini-flash-latest"
    # El modelo Pro es mejor para razonamiento complejo
    PRO_MODEL = "gemini-pro-latest"
    VISION_MODEL = "gemini-flash-latest"

    @classmethod
    def _ensure_configured(cls):
        """Asegura que genai esté configurado (lazy skip import overhead)"""
        # Usamos atributo de clase para el estado global de genai
        if not hasattr(cls, '_is_global_configured'):
            api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
            if api_key:
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)
                    cls._is_global_configured = True
                    logger.info("AIEngine: genai configured lazily.")
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
        content_list: Optional[List[Any]] = None, 
        response_schema: Optional[Type[BaseModel]] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.1,
        system_instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Llamada unificada a Gemini (Protegida por Circuit Breaker nativo de Django).
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
            from core.services.circuit_breaker import ai_circuit_breaker
            response = ai_circuit_breaker.call(
                self._execute_call_gemini,
                prompt, content_list, response_schema, model_name, temperature, system_instruction
            )
            # Si tiene éxito, reseteamos el contador de fallos
            try:
                cache.delete('gemini_fail_count')
            except: pass
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
            except:
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
                    system_instruction=system_instruction
                )

            # 6. ÚLTIMO RECURSO: Intentar sin esquema si el 404 persiste (problemas de habilitación/versión)
            if "404" in str(e) and response_schema:
                logger.warning(f"🔄 Error 404 en modo esquema. Reintentando en modo texto plano...")
                return self.call_gemini(
                    prompt=prompt,
                    content_list=content_list,
                    response_schema=None,
                    model_name=model_name,
                    temperature=temperature,
                    system_instruction=system_instruction
                )
            
            raise e

    def analyze_gds_terminal(self, raw_text: str, gds_type: str = 'SABRE') -> Dict[str, Any]:
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
            response_schema=ResultadoParseoSchema
        )
        
        # Devolvemos el schema completo (con la lista 'boletos') para el Analyzer
        return raw_response

    def parse_structured_data(
        self, 
        text: str, 
        schema: Type[BaseModel], 
        system_prompt: Optional[str] = None,
        images: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
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
        content_list: Optional[List[Any]] = None, 
        response_schema: Optional[Type[BaseModel]] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.1,
        system_instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ejecución real de la llamada (Privada para el Circuit Breaker).
        """
        import google.generativeai as genai
        if not self._ensure_configured():
            return {"error": "IA no configurada (falta API Key)"}

        try:
            # Si hay contenido multimedia, usamos el modelo de visión
            is_media = self._has_media(content_list)
            selected_model = model_name or (self.VISION_MODEL if is_media else self.DEFAULT_MODEL)

            # EL PROBLEMA: genai.GenerativeModel espera que system_instruction NO sea un booleano
            # Si se pasó algo que evaluó a False por error, lo forzamos a None
            sys_inst = system_instruction if isinstance(system_instruction, str) else None

            model = genai.GenerativeModel(
                model_name=selected_model,
                system_instruction=sys_inst
            )
            
            # Preparar inputs
            inputs = []
            if content_list:
                for item in content_list:
                    # Si ya es un dict de Gemini (mime_type, data), se pasa directo
                    if isinstance(item, (dict, list)):
                        inputs.append(item)
                    else:
                        inputs.append(str(item))
            
            if prompt:
                inputs.append(prompt)

            # Generación estructurada si hay schema
            try:
                import google.generativeai as genai
                generation_config = genai.GenerationConfig(
                    temperature=temperature,
                    response_mime_type="application/json" if response_schema else "text/plain",
                    response_schema=response_schema
                )
                response = model.generate_content(inputs, generation_config=generation_config)
            except Exception as e:
                error_str = str(e)
                # 5. INTENTO DE RESCATE: Si es un error de cuota (429), intentar con el modelo de respaldo
                if "429" in error_str and selected_model != self.FALLBACK_MODEL:
                    logger.info(f"🔄 Cuota agotada en {selected_model}. Reintentando con {self.FALLBACK_MODEL}...")
                    return self._execute_call_gemini(prompt, content_list, response_schema, self.FALLBACK_MODEL, temperature, system_instruction)
                
                # 6. ERROR DE HABILITACIÓN: Si es un 404 o dice que no está usada
                if "404" in error_str or "API has not been used" in error_str:
                    logger.error(f"❌ API DESHABILITADA o MODELO NO ENCONTRADO: {error_str}")
                    return {"error": f"La API de Gemini o el modelo {selected_model} no están disponibles. Asegúrate de que la 'Generative Language API' esté habilitada en tu proyecto de Google Cloud."}

                if response_schema:
                    import google.generativeai as genai
                    # Intento de respaldo sin forzar schema estricto
                    generation_config = genai.GenerationConfig(
                        temperature=temperature,
                        response_mime_type="application/json"
                    )
                    response = model.generate_content(inputs, generation_config=generation_config)
                else:
                    raise e

            if response_schema:
                try:
                    raw_text = response.text
                    logger.info(f"[AIEngine] Raw response text (first 500 chars): {raw_text[:500]}")
                    parsed = json.loads(raw_text)
                    return parsed
                except Exception as parse_err:
                    logger.error(f"[AIEngine] Error parseando respuesta JSON: {parse_err}")
                    return {"error": f"Error de formato en la respuesta de IA: {str(parse_err)}"}
                    return {"error": f"Respuesta no parseable: {raw_text[:200]}"}
            
            return {"text": response.text}

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "Resource exhausted" in error_str:
                logger.error(f"🚨 CUOTA AGOTADA en Gemini: {error_str}")
                raise QuotaExhaustedException(f"La cuota de la API de IA se ha agotado: {error_str}")
            
            if "API has not been used" in error_str or "disabled" in error_str.lower():
                logger.error(f"❌ API DESHABILITADA: {error_str}")
                return {"error": "La API de Gemini no está habilitada en tu proyecto de Google Cloud. Por favor, habilítala en la consola de Google Cloud para que la magia fluya."}
                
            logger.error(f"AIEngine Call Error: {traceback.format_exc()}")
            return {"error": str(e)}

    def _has_media(self, content_list: Optional[List[Any]]) -> bool:
        if not content_list:
            return False
        for item in content_list:
            if isinstance(item, dict) and "mime_type" in item:
                return True
            if hasattr(item, 'format') or "Image" in str(type(item)):
                return True
        return False

# Instancia singleton
ai_engine = AIEngine()

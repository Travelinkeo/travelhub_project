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

class AIEngine:
    """
    Motor centralizado de Inteligencia Artificial para TravelHub.
    Gestiona la configuración, modelos y llamadas estructuradas a Gemini.
    """
    
    DEFAULT_MODEL = "gemini-2.0-flash"
    VISION_MODEL = "gemini-2.0-flash"

    @classmethod
    def _ensure_configured(cls):
        """Asegura que genai esté configurado (lazy skip import overhead)"""
        # Usamos atributo de clase para el estado global de genai
        if not hasattr(cls, '_is_global_configured'):
            api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
            if api_key:
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key, transport="rest")
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
        if cache.get('gemini_circuit_open'):
            logger.critical("🛑 CIRCUIT BREAKER ACTIVO: Gemini API está inalcanzable. Abortando request para proteger workers.")
            raise CircuitBreakerException("Servicio de IA temporalmente degradado.")
            
        try:
            # 2. Intentar llamar a la IA
            from core.services.circuit_breaker import ai_circuit_breaker
            response = ai_circuit_breaker.call(
                self._execute_call_gemini,
                prompt, content_list, response_schema, model_name, temperature, system_instruction
            )
            # Si tiene éxito, reseteamos el contador de fallos
            cache.delete('gemini_fail_count')
            return response
            
        except Exception as e:
            # 3. Si falla, sumamos 1 al contador
            fails = cache.get('gemini_fail_count', 0) + 1
            cache.set('gemini_fail_count', fails, timeout=600) # Expira en 10 min
            
            logger.warning(f"⚠️ Fallo en Gemini API (Intento {fails}/5): {str(e)}")
            
            # 4. Si llegamos a 5 fallos seguidos, ABRIMOS el circuito por 5 minutos
            if fails >= 5:
                logger.critical("💥 5 Fallos consecutivos. APAGANDO conexión a Gemini por 5 minutos.")
                cache.set('gemini_circuit_open', True, timeout=300) # 5 minutos de bloqueo
                
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
                if response_schema:
                    import google.generativeai as genai
                    # Intento de respaldo sin forzar schema estricto (algunos modelos fallan con schemas complejos)
                    generation_config = genai.GenerationConfig(
                        temperature=temperature,
                        response_mime_type="application/json"
                    )
                    prompt_con_instruccion_json = f"{prompt}\n\nIMPORTANT: Return ONLY a valid JSON object."
                    # Re-intentamos con los mismos inputs pero sin schema estricto
                    response = model.generate_content(inputs, generation_config=generation_config)
                else:
                    raise e

            if response_schema:
                raw_text = response.text
                logger.info(f"[AIEngine] Raw response text (first 500 chars): {raw_text[:500]}")
                try:
                    parsed = json.loads(raw_text)
                    logger.info(f"[AIEngine] Parsed response: {parsed}")
                    return parsed
                except json.JSONDecodeError:
                    import re
                    match = re.search(r'(\{.*\}|\[.*\])', raw_text, re.DOTALL)
                    if match:
                        clean_text = match.group(0)
                        try:
                            return json.loads(clean_text)
                        except json.JSONDecodeError:
                            pass
                    logger.error(f"[AIEngine] No se pudo parsear JSON: {raw_text}")
                    return {"error": f"Respuesta no parseable: {raw_text[:200]}"}
            
            return {"text": response.text}

        except Exception as e:
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

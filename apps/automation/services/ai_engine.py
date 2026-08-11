import json
import logging
import os
import threading
import time
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Buffer de AIUsageLog para insertar en lote (P2-34). Reduce N queries a bulk_create.
_USAGE_BUFFER: list[Any] = []
_USAGE_BUFFER_LOCK = threading.Lock()
_USAGE_FLUSH_THRESHOLD = 50
_USAGE_FLUSH_MAX_AGE_SECONDS = 30
_USAGE_LAST_FLUSH_TS = time.time()

# TTL del contador cacheado de tokens diarios (P2-33).
_QUOTA_CACHE_TTL = 120

# Lua script for atomic increment with TTL (circuit breaker counter)
_INCR_FAIL_COUNT_SCRIPT = """
local key = KEYS[1]
local ttl = tonumber(ARGV[1])
local current = redis.call('INCR', key)
if current == 1 then
    redis.call('EXPIRE', key, ttl)
end
return current
"""


def _get_genai():
    """_get_genai."""
    import google.genai as genai_module

    return genai_module


def _get_genai_types():
    """_get_genai_types."""
    from google.genai import types

    return types


class CircuitBreakerException(Exception):
    """CircuitBreakerException."""

    pass


class QuotaExhaustedException(Exception):
    """QuotaExhaustedException."""

    pass


class GeminiConfigurationError(RuntimeError):
    """GeminiConfigurationError."""

    pass


def get_gemini_api_key(agency=None) -> str | None:
    """get_gemini_api_key."""
    try:
        from core.api import get_current_agency

        target_agency = agency or get_current_agency()

        if target_agency:
            try:
                config = getattr(target_agency, "configuracion_v2", None)
                if config and config.gemini_api_key:
                    return config.gemini_api_key
            except Exception as e:
                logger.debug(f"No se pudo resolver gemini_api_key de AgenciaConfiguracion: {e}")
    except Exception as e_middleware:
        logger.debug(f"Error importando o resolviendo middleware de agencia: {e_middleware}")

    return os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)


class AIEngine:
    """
    Motor centralizado de Inteligencia Artificial para TravelHub.
    Usa internamente la cadena de proveedores (ProviderChain) con fallback automático:
    Gemini → OpenAI → DeepSeek.
    """

    DEFAULT_MODEL = "gemini-2.5-flash"
    PRO_MODEL = "gemini-1.5-pro"
    VISION_MODEL = "gemini-2.5-flash"
    FALLBACK_MODEL = "gemini-2.5-flash"

    @classmethod
    def _ensure_configured(cls):
        from core.api import get_api_secret

        return bool(get_api_secret("GEMINI_API_KEY") or get_gemini_api_key())

    def __init__(self):
        """__init__."""

    @property
    def is_ready(self):
        """La IA está lista si hay una API key configurada (P3-58/59)."""
        try:
            return self._ensure_configured()
        except Exception as e:
            logger.debug(f"is_ready: error verificando configuración: {e}")
            return False

    def call_gemini(
        self,
        prompt: str,
        content_list: list[Any] | None = None,
        response_schema: type[BaseModel] | None = None,
        model_name: str | None = None,
        temperature: float = 0.1,
        system_instruction: str | None = None,
        feature: str = "generic",
        agency: Any | None = None,
    ) -> dict[str, Any]:
        """
        Punto de entrada unificado. Delega en la ProviderChain (fallback automático).
        Retorna dict con 'text' o el schema parseado, o {'error': ...}.
        """
        # 1. Circuit breaker check
        try:
            if cache.get("gemini_circuit_open"):
                logger.critical("Circuit breaker activo para Gemini. Usando cadena de fallback.")
        except Exception as e:
            logger.warning("Error checking circuit breaker: %s", e)

        # 2. Invocar cadena de proveedores vía FallbackRouter
        from apps.automation.providerchain.fallback_router import fallback_router

        images = self._prepare_images(content_list)

        result = fallback_router.generate(
            prompt=prompt,
            images=images,
            schema=response_schema,
            agency_id=getattr(agency, "id", None) if agency else None,
            feature=feature,
        )

        if result.success:
            # 3. Post-procesamiento (JSON cleaning, schema validation)
            parsed = self._postprocess_result(result.text, response_schema)
            if isinstance(parsed, dict) and "error" in parsed:
                return parsed

            # 4. Resetear contador de fallos
            try:
                cache.delete("gemini_fail_count")
            except Exception as e:
                logger.warning("Error resetting fail count: %s", e)

            # 5. Logging de uso
            self._log_usage(
                agency, result.model, feature, result.input_tokens, result.output_tokens, "SUCCESS"
            )

            if response_schema:
                return parsed
            return {"text": parsed if isinstance(parsed, str) else result.text}

        # 6. Error: incrementar contador y posiblemente abrir circuito
        try:
            client = cache.client.get_client()
            fails = client.eval(_INCR_FAIL_COUNT_SCRIPT, 1, "gemini_fail_count", 600)
            if fails >= 5:
                logger.critical(
                    "5 fallos consecutivos en la cadena de IA. Abriendo circuito por 5 min."
                )
                cache.set("gemini_circuit_open", True, timeout=300)
        except Exception as e:
            logger.warning("Error managing circuit breaker: %s", e)

        logger.error("Todos los proveedores de IA fallaron: %s", result.error)
        return {"error": result.error or "Todos los proveedores de IA fallaron."}

    def _prepare_images(self, content_list: list[Any] | None) -> list[bytes] | None:
        """Convierte content_list (formato legacy) a lista de bytes para los providers."""
        if not content_list:
            return None

        images = []
        for item in content_list:
            if isinstance(item, dict) and "data" in item:
                data = item["data"]
                images.append(data if isinstance(data, bytes) else str(data).encode())
            elif hasattr(item, "save"):
                import io

                buf = io.BytesIO()
                item.save(buf, format=getattr(item, "format", None) or "PNG")
                images.append(buf.getvalue())
            elif isinstance(item, bytes):
                images.append(item)
        return images if images else None

    def _postprocess_result(self, text: str, schema: type[BaseModel] | None) -> Any:
        """Limpia y valida la respuesta JSON contra el schema."""
        if not schema:
            return text

        cleaned = self._clean_json_response(text)
        try:
            parsed_data = json.loads(cleaned)
        except json.JSONDecodeError:
            second = self._extract_json_aggressive(cleaned)
            if second:
                try:
                    parsed_data = json.loads(second)
                except json.JSONDecodeError:
                    return {"error": "Formato JSON inválido", "raw_output": text}
            else:
                return {"error": "Formato JSON inválido", "raw_output": text}

        if isinstance(parsed_data, dict) and "error" in parsed_data:
            return parsed_data

        if schema.__name__ == "ResultadoParseoSchema":
            if isinstance(parsed_data, list):
                parsed_data = {"boletos": parsed_data}
            elif isinstance(parsed_data, dict) and "boletos" not in parsed_data:
                parsed_data = {"boletos": [parsed_data]}

        try:
            return schema(**parsed_data)
        except Exception:
            logger.debug("Pydantic v1 validation failed, trying v2")
            try:
                return schema.model_validate(parsed_data)
            except Exception:
                logger.warning("Pydantic validation failed for parsed data, returning raw")
                return parsed_data

    def analyze_gds_terminal(self, raw_text: str, gds_type: str = "SABRE") -> dict[str, Any]:
        """analyze_gds_terminal."""
        from core.api import ResultadoParseoSchema

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

        return self.call_gemini(
            prompt=f"Analiza este texto de terminal GDS:\n\n{raw_text}",
            system_instruction=system_prompt,
            response_schema=ResultadoParseoSchema,
            feature="gds_parsing",
        )

    def parse_structured_data(
        self,
        text: str,
        schema: type[BaseModel],
        system_prompt: str | None = None,
        images: list[Any] | None = None,
    ) -> dict[str, Any]:
        """parse_structured_data."""
        return self.call_gemini(
            prompt=text,
            content_list=images,
            response_schema=schema,
            system_instruction=system_prompt,
        )

    def _clean_json_response(self, text: str) -> str:
        """_clean_json_response."""
        if not text:
            return "{}"

        import re

        text = re.sub(r"```(?:json)?", "", text)
        text = text.replace("```", "")
        text = re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)

        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1:
            candidate = text[start : end + 1]
            candidate = candidate.replace("\u200b", "").replace("\ufeff", "")
            return candidate.strip()

        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            return text[start : end + 1].strip()

        return text.strip()

    def _extract_json_aggressive(self, text: str) -> str | None:
        """_extract_json_aggressive."""
        import re

        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            content = match.group(1)
            content = re.sub(r",\s*([\}\]])", r"\1", content)
            return content
        return None

    def _log_usage(self, agencia, model_name, feature, input_tokens, output_tokens, status):
        """_log_usage. Acumula en buffer y hace bulk_create (P2-34)."""
        try:
            from core.api import AIUsageLog, get_current_agency

            target_agencia = agencia or get_current_agency()

            cost = 0
            if "pro" in (model_name or ""):
                cost = 0.01
            elif "flash" in (model_name or ""):
                cost = 0.001

            log = AIUsageLog(
                agencia=target_agencia,
                model_name=model_name or "unknown",
                feature=feature,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost=cost,
                status=status,
            )

            with _USAGE_BUFFER_LOCK:
                _USAGE_BUFFER.append(log)
                buffered = len(_USAGE_BUFFER)
                buffer_age = time.time() - _USAGE_LAST_FLUSH_TS

            if buffered >= _USAGE_FLUSH_THRESHOLD or buffer_age >= _USAGE_FLUSH_MAX_AGE_SECONDS:
                self._flush_usage_buffer()

            # Contador cacheado en tiempo real (P2-33)
            self._bump_usage_counter(target_agencia, input_tokens, output_tokens)

            # Check daily quota after logging
            self._check_daily_quota_alert(target_agencia)
        except Exception as e:
            logger.error(f"Error logging AI usage: {e}")

    def _flush_usage_buffer(self):
        """Vuelca el buffer de AIUsageLog a DB con bulk_create."""
        global _USAGE_BUFFER, _USAGE_LAST_FLUSH_TS
        with _USAGE_BUFFER_LOCK:
            pending = _USAGE_BUFFER
            _USAGE_BUFFER = []
            _USAGE_LAST_FLUSH_TS = time.time()
        if not pending:
            return
        try:
            from core.api import AIUsageLog

            AIUsageLog.objects.bulk_create(pending, batch_size=500)
        except Exception as e:
            logger.error(f"Error flushing AI usage buffer ({len(pending)} rows): {e}")
            # Re-insertar al buffer para reintentar en el próximo flush
            with _USAGE_BUFFER_LOCK:
                _USAGE_BUFFER = pending + _USAGE_BUFFER

    def _usage_counter_key(self, agencia) -> str:
        return f"gemini_usage_tokens:{agencia.id}:{timezone.now().date()}"

    def _seed_usage_counter(self, agencia):
        """Siembra el contador cacheado de tokens diarios desde DB (solo si no existe)."""

        from core.models.ai import AIUsageLog

        key = self._usage_counter_key(agencia)
        if cache.get(key) is not None:
            return
        today = timezone.now().date()
        start_of_day = timezone.make_aware(
            timezone.datetime.combine(today, timezone.datetime.min.time())
        )
        usage_today = (
            AIUsageLog.objects.filter(
                agencia=agencia,
                timestamp__gte=start_of_day,
                status="SUCCESS",
            ).aggregate(total_tokens=Sum("input_tokens") + Sum("output_tokens"))["total_tokens"]
            or 0
        )
        # cache.add solo setea si la clave no existe (evita carrera de seed)
        cache.add(key, int(usage_today), timeout=_QUOTA_CACHE_TTL)

    def _bump_usage_counter(self, agencia, input_tokens, output_tokens):
        """Incrementa el contador cacheado de tokens diarios (P2-33)."""
        delta = (input_tokens or 0) + (output_tokens or 0)
        if delta <= 0:
            return
        key = self._usage_counter_key(agencia)
        try:
            cache.incr(key, delta)
        except ValueError:
            self._seed_usage_counter(agencia)
            try:
                cache.incr(key, delta)
            except Exception as e:
                logger.debug(f"No se pudo incrementar contador de uso: {e}")
        except Exception as e:
            logger.debug(f"No se pudo incrementar contador de uso: {e}")

    def _check_daily_quota_alert(self, agencia):
        """Verifica si la agencia excedió su cuota diaria y envía alerta."""
        try:
            from django.utils import timezone

            from apps.communications.services.notification_router import (
                NotificationChannel,
                NotificationContext,
                NotificationEvent,
                NotificationRecipient,
                notification_router,
            )

            # Obtener cuota diaria según plan
            plan = getattr(agencia, "plan", "FREE")
            daily_limits = {
                "FREE": 50000,  # 50k tokens/día
                "STARTER": 200000,  # 200k tokens/día
                "PROFESSIONAL": 1000000,  # 1M tokens/día
                "ENTERPRISE": 5000000,  # 5M tokens/día
            }
            daily_limit = daily_limits.get(plan, 50000)

            # Contar tokens de hoy vía contador cacheado (P2-33): evita la
            # aggregation query en cada llamada. Si expiró, se re-siembra desde DB.
            key = self._usage_counter_key(agencia)
            usage_today = cache.get(key)
            if usage_today is None:
                from django.db.models import Sum

                from core.models.ai import AIUsageLog

                today = timezone.now().date()
                start_of_day = timezone.make_aware(
                    timezone.datetime.combine(today, timezone.datetime.min.time())
                )
                usage_today = (
                    AIUsageLog.objects.filter(
                        agencia=agencia,
                        timestamp__gte=start_of_day,
                        status="SUCCESS",
                    ).aggregate(total_tokens=Sum("input_tokens") + Sum("output_tokens"))[
                        "total_tokens"
                    ]
                    or 0
                )
                cache.add(key, int(usage_today), timeout=_QUOTA_CACHE_TTL)
            usage_today = int(usage_today or 0)

            usage_pct = (usage_today / daily_limit * 100) if daily_limit > 0 else 0

            # Alertar si supera 80% o 100%
            alert_threshold = None
            if usage_today >= daily_limit:
                alert_threshold = "EXCEEDED"
            elif usage_pct >= 90:
                alert_threshold = "90%"
            elif usage_pct >= 80:
                alert_threshold = "80%"

            if alert_threshold:
                # Evitar spam: solo alertar una vez por threshold por día
                cache_key = (
                    f"gemini_quota_alert:{agencia.id}:{alert_threshold}:{timezone.now().date()}"
                )
                if not cache.get(cache_key):
                    cache.set(cache_key, True, timeout=86400)  # 24 horas

                    # Enviar alerta por Telegram y Email
                    if alert_threshold == "EXCEEDED":
                        message = (
                            f"🚨 *CUOTA GEMINI EXCEDIDA* - {agencia.nombre}\n\n"
                            f"Plan: {plan}\n"
                            f"Límite diario: {daily_limit:,} tokens\n"
                            f"Usado hoy: {usage_today:,} tokens ({usage_pct:.1f}%)\n\n"
                            f"La agencia ha SUPERADO su cuota diaria.\n"
                            f"Las nuevas requests a IA fallarán hasta mañana."
                        )
                    else:
                        message = (
                            f"⚠️ *CUOTA GEMINI ALERTA {alert_threshold}* - {agencia.nombre}\n\n"
                            f"Plan: {plan}\n"
                            f"Límite diario: {daily_limit:,} tokens\n"
                            f"Usado hoy: {usage_today:,} tokens ({usage_pct:.1f}%)\n\n"
                            f"Se acerca al límite. Considera actualizar el plan."
                        )

                    # Enviar por Telegram y Email
                    notification_router.notify(
                        NotificationContext(
                            event=NotificationEvent.ALERTA_SISTEMA,
                            recipient=NotificationRecipient(
                                nombre=f"Admin {agencia.nombre}",
                                email=getattr(settings, "ADMIN_EMAIL", None),
                                telegram_chat_id=getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", None),
                            ),
                            data={"message": message},
                            agencia_nombre=agencia.nombre,
                        ),
                        channels=[NotificationChannel.TELEGRAM, NotificationChannel.EMAIL],
                    )

        except Exception as e:
            logger.error(f"Error checking daily quota alert: {e}")


ai_engine = AIEngine()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def generate_content(prompt: str, model_name: str = "gemini-2.5-flash") -> str:
    """generate_content."""
    try:
        res = ai_engine.call_gemini(prompt, model_name=model_name)
        if isinstance(res, dict) and "text" in res:
            return res["text"]
        return str(res)
    except GeminiConfigurationError:
        raise
    except Exception:
        logger.warning("analyze_gds_terminal falló, retornando vacío", exc_info=True)
        return ""


def generate_text_from_prompt(prompt: str, model_name: str = "gemini-2.5-flash") -> str:
    """generate_text_from_prompt."""
    try:
        res = ai_engine.call_gemini(prompt, model_name=model_name)
        if isinstance(res, dict) and "text" in res:
            return res["text"]
        return str(res)
    except QuotaExhaustedException:
        logger.warning("Quota exhausted; returning fallback response.")
        return "ok"
    except Exception:
        logger.exception("Error in generate_text_from_prompt")
        return ""


def generate_structured_data(prompt: str, model_name: str = "gemini-2.5-flash") -> str:
    """generate_structured_data."""
    try:
        result = ai_engine.call_gemini(prompt, model_name=model_name)
        if isinstance(result, dict):
            return json.dumps(result)
        return result or "{}"
    except Exception:
        logger.warning(
            "generate_structured_data call_gemini falló, retornando vacío", exc_info=True
        )
        return "{}"


def analizar_documento_con_gemini_estructurado(
    file_bytes: bytes,
    mime_type: str,
    prompt_text: str,
    response_schema: type,
) -> dict:
    """Analiza un documento (PDF/imagen) con la cadena de proveedores."""
    from apps.automation.providerchain.fallback_router import fallback_router

    result = fallback_router.generate(
        prompt=prompt_text,
        images=[file_bytes],
        schema=response_schema,
        feature="document_analysis",
    )

    if result.success:
        try:
            return json.loads(result.text)
        except json.JSONDecodeError as e:
            raise ValueError(f"El proveedor no devolvió un JSON válido: {result.text[:200]}") from e
    else:
        raise ValueError(f"Todos los proveedores fallaron: {result.error}")


def list_available_models():
    """Lista los modelos disponibles en la cuenta Gemini."""
    genai = _get_genai()
    api_key = get_gemini_api_key()
    if not api_key:
        return "Error: No se proporciono API Key."
    try:
        client = genai.Client(api_key=api_key)
        return [m.name for m in client.models.list()]
    except Exception as e:
        logger.error(f"Error al listar modelos: {e}")
        return f"Error: {e}"

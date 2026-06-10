import logging
import time

from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

PLAN_LIMITS = getattr(settings, "SAAS_PLAN_LIMITS", {})

AI_RATE_LIMITS = {
    "FREE": {"max_calls": 20, "window_seconds": 86400},
    "BASIC": {"max_calls": 50, "window_seconds": 86400},
    "PRO": {"max_calls": 200, "window_seconds": 86400},
    "ENTERPRISE": {"max_calls": 1000, "window_seconds": 86400},
}

DEFAULT_AI_LIMIT = {"max_calls": 50, "window_seconds": 86400}

_MAX_MEMORY_ENTRIES = 10000


class AIRateLimitMiddleware(MiddlewareMixin):
    """
    Middleware que limita las llamadas a endpoints de IA por agencia (tenant).
    Usa Redis como backend de conteo si está disponible, con fallback a memoria.
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        self._memory_store = {}

    @staticmethod
    def _get_plan_limits(agencia):
        plan = getattr(agencia, "plan", "FREE") or "FREE"
        return AI_RATE_LIMITS.get(plan, DEFAULT_AI_LIMIT)

    def _check_rate_limit(self, agencia_id, plan):
        limit_config = AI_RATE_LIMITS.get(plan, DEFAULT_AI_LIMIT)
        max_calls = limit_config["max_calls"]
        window = limit_config["window_seconds"]
        key = f"ai_rate:{agencia_id}:{int(time.time() // window)}"

        try:
            from django.core.cache import cache

            try:
                count = cache.incr(key)
            except ValueError:
                cache.set(key, 1, timeout=window + 60)
                count = 1
            if count > max_calls:
                return False, max_calls, count
            return True, max_calls, count
        except Exception:
            current_bucket = int(time.time() // window)
            if len(self._memory_store) > _MAX_MEMORY_ENTRIES:
                expired_keys = [
                    k
                    for k in self._memory_store
                    if k.endswith(f":{current_bucket - 1}") or k.endswith(f":{current_bucket - 2}")
                ]
                for k in expired_keys[: len(self._memory_store) - _MAX_MEMORY_ENTRIES // 2]:
                    self._memory_store.pop(k, None)

            current = self._memory_store.get(key, 0)
            if current >= max_calls:
                return False, max_calls, current
            self._memory_store[key] = current + 1
            return True, max_calls, current + 1

    def process_request(self, request):
        agencia = getattr(request, "agencia", None) or getattr(request, "agency", None)
        if not agencia:
            return None

        ai_prefixes = ("/api/ai/", "/api/chat/", "/api/v1/ai/", "/api/v1/chat/")
        if not any(request.path.startswith(p) for p in ai_prefixes):
            return None

        plan = getattr(agencia, "plan", "FREE") or "FREE"
        allowed, max_calls, current = self._check_rate_limit(agencia.id, plan)

        if not allowed:
            logger.warning(
                f"AI rate limit exceeded for agencia {agencia.id} (plan: {plan}): {current}/{max_calls}"
            )
            return JsonResponse(
                {
                    "error": "Límite de consultas de IA alcanzado para tu plan",
                    "plan": plan,
                    "limit": max_calls,
                    "used": current,
                    "upgrade_url": "/billing/upgrade/",
                },
                status=429,
            )

        return None

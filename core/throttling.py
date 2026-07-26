# core/throttling.py
from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle

_THROTTLE_RATES = getattr(settings, "REST_FRAMEWORK", {}).get("DEFAULT_THROTTLE_RATES", {})


class DashboardRateThrottle(UserRateThrottle):
    """DashboardRateThrottle."""

    scope = "dashboard"

    @property
    def rate(self):
        return _THROTTLE_RATES.get(self.scope, "100/hour")


class LiquidacionRateThrottle(UserRateThrottle):
    """LiquidacionRateThrottle."""

    scope = "liquidacion"

    @property
    def rate(self):
        return _THROTTLE_RATES.get(self.scope, "50/hour")


class ReportesRateThrottle(UserRateThrottle):
    """ReportesRateThrottle."""

    scope = "reportes"

    @property
    def rate(self):
        return _THROTTLE_RATES.get(self.scope, "20/hour")


class UploadRateThrottle(UserRateThrottle):
    """UploadRateThrottle."""

    scope = "upload"

    @property
    def rate(self):
        return _THROTTLE_RATES.get(self.scope, "30/hour")


class AgenciaAIParserThrottle(SimpleRateThrottle):
    """
    FRENOS ABS: Escudo Financiero para la API de Gemini.
    Limita las peticiones basándose en el ID de la Agencia, no en la IP.
    Evita que una agencia (o un bot vulnerando una cuenta) consuma todo el presupuesto.
    """

    # Este nombre ('ai_parser_quota') se conectará con settings.py
    scope = "ai_parser_quota"

    def get_cache_key(self, request, view):
        """get_cache_key."""
        # Resolver la agencia desde el request o desde la relación de usuario si está autenticado
        agencia = getattr(request, "agencia", getattr(request, "agency", None))

        if not agencia and request.user.is_authenticated:
            from core.security import get_user_active_agency

            agencia = get_user_active_agency(request.user)

        agencia_id = agencia.id if agencia else None

        if request.user.is_authenticated and agencia_id:
            # El límite es global para toda la agencia
            ident = f"agencia_{agencia_id}"
        else:
            # 2. Fallback: Si no hay agencia (ej. un endpoint público temporal), usamos la IP
            ident = self.get_ident(request)

        return self.cache_format % {"scope": self.scope, "ident": ident}


class AIParserDailyQuotaThrottle(AgenciaAIParserThrottle):
    """
    Mecanismo de cuota diaria estricta (ej. 100 parseos por día por Agencia).
    """

    scope = "ai_parser_daily"

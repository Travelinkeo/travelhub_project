# core/throttling.py
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle, SimpleRateThrottle


class DashboardRateThrottle(UserRateThrottle):
    """Rate limit específico para dashboard (más permisivo)"""
    scope = 'dashboard'
    rate = '100/hour'


class LiquidacionRateThrottle(UserRateThrottle):
    """Rate limit para operaciones de liquidación"""
    scope = 'liquidacion'
    rate = '50/hour'


class ReportesRateThrottle(UserRateThrottle):
    """Rate limit para generación de reportes (más restrictivo)"""
    scope = 'reportes'
    rate = '20/hour'


class UploadRateThrottle(UserRateThrottle):
    """Rate limit para uploads (pasaportes, boletos)"""
    scope = 'upload'
    rate = '30/hour'


class AgenciaAIParserThrottle(SimpleRateThrottle):
    """
    FRENOS ABS: Escudo Financiero para la API de Gemini.
    Limita las peticiones basándose en el ID de la Agencia, no en la IP.
    Evita que una agencia (o un bot vulnerando una cuenta) consuma todo el presupuesto.
    """
    # Este nombre ('ai_parser_quota') se conectará con settings.py
    scope = 'ai_parser_quota'

    def get_cache_key(self, request, view):
        # 1. Si el usuario está autenticado y pertenece a una agencia
        # Nota: Usamos la lógica de resolución de agencia del middleware si está disponible
        agencia_id = getattr(request.user, 'agencia_id', None)
        
        # Fallback a request.agencia si existe (seteado por middleware)
        if not agencia_id and hasattr(request, 'agencia') and request.agencia:
            agencia_id = request.agencia.id

        if request.user.is_authenticated and agencia_id:
            # El límite es global para toda la agencia
            ident = f"agencia_{agencia_id}"
        else:
            # 2. Fallback: Si no hay agencia (ej. un endpoint público temporal), usamos la IP
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class AIParserDailyQuotaThrottle(AgenciaAIParserThrottle):
    """
    Mecanismo de cuota diaria estricta (ej. 100 parseos por día por Agencia).
    """
    scope = 'ai_parser_daily'


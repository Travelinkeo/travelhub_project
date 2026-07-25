"""
Autenticación por API Key para DRF.

Los clientes envían la key en el header X-API-Key.
La autenticación verifica el hash, rate limits, y scopes.
"""

import logging

from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission

from core.models.cron_api_key import CronApiKey

logger = logging.getLogger(__name__)


class APIKeyAuthentication(BaseAuthentication):
    """
    Autenticación por API Key via header X-API-Key.

    Uso:
        class MyView(APIKeyAuthentication, APIView):
            ...
    """

    keyword = "X-API-Key"

    def authenticate(self, request):
        """Método: authenticate."""
        api_key_raw = request.META.get(f"HTTP_{self.keyword.replace('-', '_').upper()}")

        if not api_key_raw:
            return None  # No autenticar — dejar que otros métodos intenten

        api_key = CronApiKey.verify(api_key_raw)
        if api_key is None:
            raise exceptions.AuthenticationFailed(
                "API key inválida o expirada.",
                code="invalid_api_key",
            )

        # Rate limiting básico
        from core.api.rate_limit import check_rate_limit

        allowed, remaining = check_rate_limit(api_key)
        if not allowed:
            raise exceptions.Throttled(
                detail=f"Rate limit excedido ({api_key.rate_limit} req/hora). "
                f"Plan actual: {api_key.get_plan_display()}.",
            )

        # Agregar rate limit info al request para headers de respuesta
        request._api_key = api_key
        request._rate_remaining = remaining

        # Usar el usuario que creó la key como request.user
        return (api_key.user, api_key)

    def authenticate_header(self, request):
        """Método: authenticate header."""
        return self.keyword


class HasAPIKeyScope(BasePermission):
    """
    Verifica que la API key tenga un scope específico.

    Uso:
        class MyView(APIKeyAuthentication, APIView):
            permission_classes = [HasAPIKeyScope("read:ventas")]
    """

    def __init__(self, required_scope):
        self.required_scope = required_scope

    def has_permission(self, request, view):
        """Método que verifica  permission. Returns: bool."""
        api_key = getattr(request, "_api_key", None)
        if api_key is None:
            return False

        # Sin scopes definidos = acceso total (backward compatible)
        if not api_key.scopes:
            return True

        return self.required_scope in api_key.scopes


def api_key_required(scope=None):
    """
    Decorador shortcut para views que requieren API key.

    Uso:
        @api_key_required("read:ventas")
        def my_view(request):
            ...
    """
    from rest_framework.decorators import api_view, permission_classes

    def decorator(view_func):
        """Función: decorator."""
        wrapped = api_view(["GET", "POST", "PUT", "PATCH", "DELETE"])(view_func)
        perms = [APIKeyAuthentication]
        if scope:
            perms.append(HasAPIKeyScope(scope))
        return permission_classes(perms)(wrapped)

    return decorator

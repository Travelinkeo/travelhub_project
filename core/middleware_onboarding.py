"""
Middleware que redirige a los usuarios nuevos a través del
Onboarding Wizard si no han completado la configuración inicial
de su agencia.

Se salta la redirección para:
- Rutas de onboarding (/onboarding/)
- Admin (/admin/)
- Archivos estáticos (/static/)
- Endpoints de API (/api/, /health/)
- Login/logout
- Landing page pública
"""

import logging
import re

from django.shortcuts import redirect

from core.models.agencia import UsuarioAgencia

logger = logging.getLogger(__name__)

# Rutas exentas del onboarding — regex (sin anclaje inicial)
ONBOARDING_SKIP_PATHS = re.compile(
    r"^(/onboarding/"
    r"|/admin/"
    r"|/static/"
    r"|/api/"
    r"|/health/"
    r"|/login"
    r"|/logout"
    r"|/auth/"
    r"|/accounts/"
    r"|/docs/"
    r"|/status/"
    r"|/pricing/"
    r"|/manifest.json"
    r"|/service-worker.js"
    r"|/offline/"
    r"|/sso/"
    r"|/favicon)"
)


class OnboardingRedirectMiddleware:
    """Redirige usuarios autenticados sin onboarding a /onboarding/."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Solo para usuarios autenticados
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Saltar rutas exentas
        path = request.path_info
        if ONBOARDING_SKIP_PATHS.match(path):
            return self.get_response(request)

        # Verificar si el usuario ha completado onboarding
        if self._needs_onboarding(request.user):
            return redirect("onboarding_start")

        return self.get_response(request)

    @staticmethod
    def _needs_onboarding(user):
        """True si el usuario necesita completar onboarding.

        El onboarding se completa cuando el usuario tiene al menos
        una relación UsuarioAgencia (está asociado a una agencia).
        """
        try:
            return not UsuarioAgencia.objects.filter(usuario=user).exists()
        except Exception:
            return False

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

        # No interceptar requests HTMX (navegación parcial del wizard)
        if request.headers.get("HX-Request"):
            return self.get_response(request)

        # Verificar si el usuario ha completado onboarding
        if self._needs_onboarding(request.user):
            return redirect("onboarding_welcome")

        # Verificar si la agencia necesita setup post-registro (wizard)
        agencia = getattr(request, "agencia", None)
        if path != "/onboarding/wizard/" and self._needs_agency_setup(agencia):
            return redirect("core:onboarding_wizard")

        return self.get_response(request)

    @staticmethod
    def _needs_onboarding(user):
        """True si el usuario necesita completar onboarding.

        El onboarding se considera completado si el usuario ya tiene una
        relación UsuarioAgencia (está asociado a una agencia) o si su
        UserProgress del wizard llegó al paso final (STEP_COMPLETE).
        """
        try:
            has_agency = UsuarioAgencia.objects.filter(usuario=user).exists()
        except Exception:
            has_agency = False
        if has_agency:
            return False

        from apps.common.models import UserProgress

        try:
            progress = UserProgress.objects.get(user=user)
        except UserProgress.DoesNotExist:
            return True
        return not progress.onboarding_completed

    @staticmethod
    def _needs_agency_setup(agencia):
        """True si la agencia necesita el wizard de setup post-registro."""
        if not agencia:
            return False
        from core.models.onboarding import AgenciaSetupProgress
        progress = AgenciaSetupProgress.objects.filter(agencia=agencia).first()
        return progress is not None and not progress.is_completed

"""
Middleware que verifica los límites del plan de la agencia
y bloquea acciones que excedan el plan contratado.

Límites evaluados:
- Número de usuarios
- Ventas por mes
- Almacenamiento (proximamente)

Se integra con SAAS_PLAN_LIMITS de settings.py.
"""

import logging

from django.shortcuts import redirect

logger = logging.getLogger(__name__)

# Rutas exentas de verificación de límites
LIMIT_SKIP_PATHS = (
    "/admin/",
    "/account/billing/",
    "/api/",
    "/health/",
    "/static/",
    "/login",
    "/logout",
    "/onboarding/",
    "/pricing/",
    "/status/",
)


class PlanLimitMiddleware:
    """Verifica que la agencia no exceda los límites de su plan."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Método interna: call."""
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Saltar rutas exentas
        path = request.path_info
        if path.startswith(LIMIT_SKIP_PATHS):
            return self.get_response(request)

        # Saltar requests que no modifican datos
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return self.get_response(request)

        # Obtener agencia del usuario
        agencia = self._get_agency(request.user)
        if not agencia:
            return self.get_response(request)

        config = agencia.configuracion
        if not config:
            return self.get_response(request)

        # Verificar estado del plan
        if config.plan_status in ("cancelled", "expired"):
            logger.warning(f"Agencia {agencia.id} bloqueada: plan {config.plan_status}")
            from django.contrib import messages

            messages.error(
                request,
                "Tu plan ha sido suspendido. "
                "Actualiza tu suscripción para continuar usando el sistema.",
            )
            return redirect("account_billing")

        # Verificar límite de ventas del mes (para rutas POST de ventas)
        if "venta" in path.lower() or "bookings" in path.lower():
            limite = config.limite_ventas_mes
            actual = config.ventas_mes_actual
            if actual >= limite:
                from django.contrib import messages

                messages.warning(
                    request,
                    f"Has alcanzado el límite de {limite} ventas de tu plan "
                    f"({config.plan}). Actualiza tu plan para continuar.",
                )
                return redirect("account_billing")

        return self.get_response(request)

    @staticmethod
    def _get_agency(user):
        """Obtiene la primera agencia activa del usuario."""
        ua = user.agencias.select_related("agencia__configuracion").first()
        return ua.agencia if ua else None

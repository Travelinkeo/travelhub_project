"""
Middleware para verificar limites del plan SaaS.
Protege rutas de creacion de recursos en toda la plataforma.
"""
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect

CREATION_ENDPOINTS = [
    "/api/ventas/",
    "/ventas/nueva/",
    "/api/cotizaciones/",
    "/cotizaciones/nueva/",
    "/api/clientes/",
    "/api/proveedores/",
    "/api/productos/",
    "/api/pasajeros/",
    "/upload/",
]


class SaaSLimitMiddleware:
    """Middleware que verifica los limites del plan SaaS en toda ruta de creacion."""

    def __init__(self, get_response):
        self.get_response = get_response

    def _get_plan_limits(self, agencia):
        plan_key = agencia.plan if agencia.plan else "FREE"
        plan_limits = getattr(settings, "SAAS_PLAN_LIMITS", {})
        limits = plan_limits.get(plan_key, plan_limits.get("FREE", {}))
        return {
            "users": limits.get(
                "users",
                agencia.limite_usuarios if hasattr(agencia, "limite_usuarios") else 2,
            ),
            "sales_per_month": limits.get(
                "sales_per_month",
                agencia.limite_ventas_mes if hasattr(agencia, "limite_ventas_mes") else 50,
            ),
        }

    def _is_creation_endpoint(self, path):
        for pattern in CREATION_ENDPOINTS:
            if pattern in path:
                return True
        return False

    def _build_error_response(self, agencia, plan_limits, message_key):
        sales_limit = plan_limits["sales_per_month"]
        return JsonResponse(
            {
                "error": message_key,
                "plan_actual": agencia.plan,
                "limite": sales_limit,
                "usado": agencia.ventas_mes_actual,
                "upgrade_url": "/billing/upgrade/",
            },
            status=403,
        )

    def __call__(self, request):
        agencia = getattr(request, "agencia", None)

        if request.user.is_authenticated and not request.user.is_superuser and agencia:
            if request.method == "POST" and self._is_creation_endpoint(request.path):
                plan_limits = self._get_plan_limits(agencia)

                if not agencia.puede_crear_venta():
                    messages.error(
                        request,
                        f"Has alcanzado el limite de {plan_limits['sales_per_month']} ventas/mes de tu plan {agencia.get_plan_display()}. "
                        "Actualiza tu plan para continuar.",
                    )
                    if request.path.startswith("/api/"):
                        return self._build_error_response(agencia, plan_limits, "Limite de ventas alcanzado")
                    return redirect("/billing/pricing/")

                if request.path in ["/api/clientes/", "/api/proveedores/", "/api/productos/"] and not agencia.puede_agregar_usuario():
                    messages.error(
                        request,
                        "Has alcanzado el limite de recursos de tu plan. Actualiza tu plan para continuar.",
                    )
                    if request.path.startswith("/api/"):
                        return JsonResponse(
                            {
                                "error": "Limite de recursos alcanzado",
                                "plan_actual": agencia.plan,
                                "upgrade_url": "/billing/upgrade/",
                            },
                            status=403,
                        )
                    return redirect("/billing/pricing/")

        response = self.get_response(request)
        return response

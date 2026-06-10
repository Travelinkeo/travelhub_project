import logging

from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.template import TemplateDoesNotExist

from apps.common.services.saas_quota_service import SaaSQuotaService

logger = logging.getLogger(__name__)


class SaaSLimitMiddleware:
    """
    Interceptor de tráfico para Enforcement de Cuotas SaaS.
    Bloquea operaciones de escritura si la agencia supera su límite.
    """

    # MAPA CORREGIDO: Se incluyen los endpoints de IA y Parsing de Boletos
    RESOURCE_ACTION_MAP = {
        "/ventas/nueva/": "sales_per_month",
        "/api/ventas/": "sales_per_month",
        "/cotizaciones/nueva/": "leads_per_month",
        "/api/cotizaciones/": "leads_per_month",
        "/agencia/usuarios/agregar/": "users",
        # FIX: Endpoints de boletos añadidos al enforcement
        "/api/boletos/upload/": "sales_per_month",
        "/boletos/importar/": "sales_per_month",
        "/erp/boletos-importar/": "sales_per_month",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in ["POST", "PUT", "PATCH"]:
            # Identificar si la ruta actual está en nuestro mapa de recursos controlados
            resource_type = None
            for path, res_type in self.RESOURCE_ACTION_MAP.items():
                if request.path.startswith(path):
                    resource_type = res_type
                    break

            if resource_type:
                # Obtener agencia del contexto global inyectado por ThreadLocalContextMiddleware
                agencia = getattr(request, "agencia", getattr(request, "agency", None))

                if agencia:
                    has_quota = SaaSQuotaService.check_quota(agencia, resource_type)

                    if not has_quota:
                        limits = SaaSQuotaService.get_limits(agencia)
                        limit = limits.get(resource_type, 0)
                        logger.warning(
                            f"SaaS Enforcement: Agencia {agencia.id} excedió límite de {resource_type}."
                        )

                        if request.headers.get(
                            "Accept"
                        ) == "application/json" or request.headers.get("HX-Request"):
                            return JsonResponse(
                                {
                                    "error": "upgrade_required",
                                    "message": f"Has alcanzado el límite de tu plan ({limit}). Actualiza para continuar.",
                                },
                                status=403,
                            )

                        try:
                            return HttpResponseForbidden(
                                render(
                                    request,
                                    "core/upgrade_required.html",
                                    {"resource": resource_type, "limit": limit},
                                )
                            )
                        except TemplateDoesNotExist:
                            return HttpResponseForbidden(
                                f"Has alcanzado el límite de {resource_type} ({limit}). Por favor, actualiza tu plan."
                            )

        return self.get_response(request)

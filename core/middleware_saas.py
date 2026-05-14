"""
Middleware para la aplicación de cuotas SaaS en TravelHub.
Intercepta peticiones de creación para asegurar el cumplimiento de los límites del plan.
"""

import logging
from django.conf import settings
from django.shortcuts import redirect, render
from django.http import JsonResponse
from apps.common.services.saas_quota_service import SaaSQuotaService

logger = logging.getLogger(__name__)

# Mapeo de fragmentos de URL a tipos de recursos en SAAS_PLAN_LIMITS
RESOURCE_ACTION_MAP = {
    '/ventas/': 'sales_per_month',
    '/venta/': 'sales_per_month',
    '/cotizaciones/': 'leads_per_month',
    '/cotizacion/': 'leads_per_month',
    '/oportunidades/': 'leads_per_month',
    '/clientes/add/': 'leads_per_month',
    '/usuarios/': 'users',
}

class SaaSLimitMiddleware:
    """
    Middleware que realiza el Enforcement de cuotas SaaS.
    Solo actúa sobre métodos POST que intentan crear nuevos recursos.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Filtro inicial: Solo POST y usuarios autenticados con agencia
        if request.method == "POST" and request.user.is_authenticated and not request.user.is_superuser:
            agencia = getattr(request, "agencia", None)
            if agencia:
                path = request.path.lower()
                
                # 2. Identificar si el endpoint corresponde a un recurso limitado
                resource_type = None
                for pattern, r_type in RESOURCE_ACTION_MAP.items():
                    if pattern in path:
                        resource_type = r_type
                        break
                
                # 3. Ejecutar validación de cuota usando el servicio (Caché Redis)
                if resource_type:
                    if not SaaSQuotaService.check_quota(agencia, resource_type):
                        return self._handle_limit_exceeded(request, agencia, resource_type)

        return self.get_response(request)

    def _handle_limit_exceeded(self, request, agencia, resource_type):
        """
        Intervención cuando se supera el límite.
        """
        plan = agencia.plan
        limits = settings.SAAS_PLAN_LIMITS.get(plan, settings.SAAS_PLAN_LIMITS['FREE'])
        limit_value = limits.get(resource_type, 0)
        
        msg = f"Límite de {resource_type.replace('_', ' ')} alcanzado ({limit_value})."
        
        # Respuesta para API
        if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                "error": "PLAN_LIMIT_EXCEEDED",
                "message": msg,
                "resource": resource_type,
                "limit": limit_value,
                "plan": plan,
                "upgrade_url": "/billing/upgrade/"
            }, status=403)
        
        # Respuesta para Web (Redirección o Render)
        # Podemos renderizar una plantilla de "Upgrade" o redirigir con un mensaje
        from django.contrib import messages
        messages.warning(request, f"🚀 {msg} Tu plan actual ({plan}) no permite crear más registros. ¡Haz un upgrade para crecer!")
        
        # Intentar renderizar una página dedicada si existe, si no, redirigir a pricing
        try:
            return render(request, 'errors/saas_limit.html', {
                'agencia': agencia,
                'resource': resource_type,
                'limit': limit_value
            }, status=403)
        except:
            return redirect('/billing/pricing/')

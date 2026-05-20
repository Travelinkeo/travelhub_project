import logging
from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.core.cache import cache

logger = logging.getLogger(__name__)

class SaasQuotaService:
    """
    Servicio centralizado para validación de cuotas SaaS respaldado por Redis.
    """
    @staticmethod
    def check_quota(agencia_id, plan_name, resource_type):
        limits = settings.SAAS_PLAN_LIMITS.get(plan_name.upper(), settings.SAAS_PLAN_LIMITS['FREE'])
        limit = limits.get(resource_type, 0)
        
        # Redis cache key
        cache_key = f"quota_{agencia_id}_{resource_type}_current_month"
        current_usage = cache.get(cache_key, 0)
        
        return current_usage < limit, current_usage, limit

class SaaSLimitMiddleware:
    """
    Interceptor de tráfico para Enforcement de Cuotas SaaS.
    Bloquea operaciones de escritura si la agencia supera su límite.
    """
    # MAPA CORREGIDO: Se incluyen los endpoints de IA y Parsing de Boletos
    RESOURCE_ACTION_MAP = {
        '/ventas/nueva/': 'sales_per_month',
        '/api/ventas/': 'sales_per_month',
        '/cotizaciones/nueva/': 'leads_per_month',
        '/api/cotizaciones/': 'leads_per_month',
        '/agencia/usuarios/agregar/': 'users',
        # FIX: Endpoints de boletos añadidos al enforcement
        '/api/boletos/upload/': 'sales_per_month',
        '/boletos/importar/': 'sales_per_month',
        '/erp/boletos-importar/': 'sales_per_month',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in ['POST', 'PUT', 'PATCH']:
            # Identificar si la ruta actual está en nuestro mapa de recursos controlados
            resource_type = None
            for path, res_type in self.RESOURCE_ACTION_MAP.items():
                if path in request.path:
                    resource_type = res_type
                    break
            
            if resource_type:
                # Obtener agencia del contexto global inyectado por ThreadLocalContextMiddleware
                agencia = getattr(request, 'agencia', getattr(request, 'agency', None))
                
                if agencia:
                    plan_name = getattr(agencia, 'plan', 'FREE')
                    
                    has_quota, current, limit = SaasQuotaService.check_quota(
                        agencia.id, 
                        plan_name, 
                        resource_type
                    )
                    
                    if not has_quota:
                        logger.warning(f"SaaS Enforcement: Agencia {agencia.id} excedió límite de {resource_type} ({limit}).")
                        
                        if request.headers.get('Accept') == 'application/json' or request.headers.get('HX-Request'):
                            return JsonResponse({
                                'error': 'upgrade_required',
                                'message': f'Has alcanzado el límite de tu plan ({limit}). Actualiza para continuar.'
                            }, status=403)
                        
                        try:
                            return HttpResponseForbidden(render(request, 'core/upgrade_required.html', {
                                'resource': resource_type,
                                'limit': limit
                            }))
                        except:
                            # Fallback if template doesn't exist
                            return HttpResponseForbidden(f"Has alcanzado el límite de {resource_type} ({limit}). Por favor, actualiza tu plan.")

        return self.get_response(request)

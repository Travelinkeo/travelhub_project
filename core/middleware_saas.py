"""
Middleware para verificar límites del plan SaaS.
"""
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages


class SaaSLimitMiddleware:
    """Middleware que verifica los límites del plan SaaS."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def _get_plan_limits(self, agencia):
        """Obtiene los límites del plan desde settings, con fallback a los del modelo."""
        plan_key = agencia.plan if agencia.plan else 'FREE'
        plan_limits = getattr(settings, 'SAAS_PLAN_LIMITS', {})
        limits = plan_limits.get(plan_key, plan_limits.get('FREE', {}))
        return {
            'users': limits.get('users', agencia.limite_usuarios if hasattr(agencia, 'limite_usuarios') else 2),
            'sales_per_month': limits.get('sales_per_month', agencia.limite_ventas_mes if hasattr(agencia, 'limite_ventas_mes') else 50),
        }

    def __call__(self, request):
        # ThreadLocalContextMiddleware ya configuró request.agencia
        agencia = getattr(request, 'agencia', None)
        
        if request.user.is_authenticated and not request.user.is_superuser and agencia:
            if request.method == 'POST':
                plan_limits = self._get_plan_limits(agencia)
                sales_limit = plan_limits['sales_per_month']
                
                # Límite de ventas
                if '/api/ventas/' in request.path or '/ventas/nueva/' in request.path:
                    if not agencia.puede_crear_venta():
                        messages.error(
                            request,
                            f'Has alcanzado el límite de {sales_limit} ventas/mes de tu plan {agencia.get_plan_display()}. '
                            'Actualiza tu plan para continuar.'
                        )
                        if request.path.startswith('/api/'):
                            from django.http import JsonResponse
                            return JsonResponse({
                                'error': 'Límite de ventas alcanzado',
                                'plan_actual': agencia.plan,
                                'limite': sales_limit,
                                'usado': agencia.ventas_mes_actual,
                                'upgrade_url': '/billing/upgrade/'
                            }, status=403)
                        return redirect('/billing/pricing/')
        
        response = self.get_response(request)
        return response
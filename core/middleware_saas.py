"""
Middleware para verificar límites del plan SaaS.
"""
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from core.models.agencia import Agencia


class SaaSLimitMiddleware:
    """Middleware que verifica los límites del plan SaaS."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Solo verificar para usuarios autenticados
        if request.user.is_authenticated and not request.user.is_superuser:
            # Obtener agencia del usuario
            try:
                usuario_agencia = request.user.agencias.filter(activo=True).first()
                if usuario_agencia:
                    agencia = usuario_agencia.agencia
                    
                    # Guardar agencia en request para uso posterior
                    request.agencia = agencia
                    
                    # Verificar si está intentando crear una venta
                    if request.method == 'POST' and '/api/ventas/' in request.path:
                        if not agencia.puede_crear_venta():
                            messages.error(
                                request,
                                f'Has alcanzado el límite de {agencia.limite_ventas_mes} ventas/mes de tu plan {agencia.get_plan_display()}. '
                                'Actualiza tu plan para continuar.'
                            )
                            # En API, retornar error JSON
                            if request.path.startswith('/api/'):
                                from django.http import JsonResponse
                                return JsonResponse({
                                    'error': 'Límite de ventas alcanzado',
                                    'plan_actual': agencia.plan,
                                    'limite': agencia.limite_ventas_mes,
                                    'usado': agencia.ventas_mes_actual,
                                    'upgrade_url': '/billing/upgrade/'
                                }, status=403)
            except Exception:
                pass
        
        response = self.get_response(request)
        return response

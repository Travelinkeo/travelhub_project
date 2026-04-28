"""
Middleware para verificar límites del plan SaaS.
"""
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from django.urls import reverse
# from core.models.agencia import Agencia # Avoid circular import if possible, or keep if needed later


class SaaSLimitMiddleware:
    """Middleware que verifica los límites del plan SaaS."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Inicializar atributo para evitar AttributeError
        request.agencia = None
        
        # Solo verificar para usuarios autenticados
        if request.user.is_authenticated:
            # 1. Intentar obtener la agencia (incluso para superusers)
            try:
                # 'agencias' es el related_name de UsuarioAgencia
                usuario_agencia = request.user.agencias.filter(activo=True).select_related('agencia').first()
                if usuario_agencia:
                    request.agencia = usuario_agencia.agencia
                
                # 1b. Si es superuser y no tiene agencia asignada, intentar buscar la primera activa
                # o una que sea de su propiedad
                if not request.agencia and request.user.is_superuser:
                    from core.models.agencia import Agencia
                    # Prioridad: Agencia de la cual es propietario
                    agencia = Agencia.objects.filter(propietario=request.user, activa=True).first()
                    # Fallback: Primera agencia activa en el sistema
                    if not agencia:
                        agencia = Agencia.objects.filter(activa=True).first()
                    request.agencia = agencia
            except Exception:
                pass

            # 2. Verificar límites (SOLO si NO es superuser y TIENE agencia)
            if not request.user.is_superuser and request.agencia:
                agencia = request.agencia
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
        
        response = self.get_response(request)
        return response

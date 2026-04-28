from django.views.generic import View
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from core.models.notificaciones import NotificacionInteligente

class HTMXNotificacionesVivasView(LoginRequiredMixin, View):
    """
    Endpoint reactivo para HTMX Polling. 
    Devuelve las notificaciones pendientes del usuario y las marca como leídas.
    """
    def get(self, request, *args, **kwargs):
        # Obtenemos las notificaciones no leídas
        notificaciones = NotificacionInteligente.objects.filter(
            usuario=request.user,
            leida=False
        ).order_by('creado_en')
        
        if not notificaciones.exists():
            # Si no hay notificaciones, HTMX no inyectará nada (Empty Response)
            return HttpResponse("")

        # Convertimos a lista para el context antes de actualizar
        lista_notificaciones = list(notificaciones)
        
        # Marcamos como leídas en lote para eficiencia
        notificaciones.update(leida=True)
        
        return render(request, 'core/partials/magic_toasts.html', {
            'notificaciones': lista_notificaciones
        })

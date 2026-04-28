from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from core.models.notificaciones import NotificacionAgente

@login_required
def notificaciones_live_view(request):
    """
    Controlador de Polling HTMX: Recupera notificaciones no leídas para el usuario actual.
    Si existen, las marca como leídas y las renderiza como Toasts.
    """
    notificaciones = NotificacionAgente.objects.filter(usuario=request.user, leida=False)
    
    if notificaciones.exists():
        # Capturamos el conjunto para el contexto antes de marcarlas como leídas
        context = {'notificaciones': list(notificaciones)}
        
        # Marcamos como leídas en lote para eficiencia
        notificaciones.update(leida=True)
        
        return render(request, 'core/partials/live_toasts.html', context)
    
    # Si no hay nada nuevo, devolvemos vacío (200 OK para HTMX)
    return HttpResponse('')

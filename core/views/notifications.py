from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.automation.models import NotificacionAgente


@login_required
def notificaciones_live_view(request):
    """
    Controlador de Polling HTMX: Recupera notificaciones no leídas para el usuario actual.
    Si existen, las marca como leídas y las renderiza como Toasts.
    """
    notificaciones = NotificacionAgente.objects.filter(usuario=request.user, leida=False)

    if notificaciones.exists():
        # Capturamos el conjunto para el contexto antes de marcarlas como leídas
        context = {"notificaciones": list(notificaciones)}

        # Marcamos como leídas en lote para eficiencia
        notificaciones.update(leida=True)

        return render(request, "core/partials/live_toasts.html", context)

    # Si no hay nada nuevo, devolvemos vacío (200 OK para HTMX)
    return HttpResponse("")


@login_required
def notificaciones_panel_view(request):
    """
    Devuelve el historial de las últimas 30 notificaciones del usuario
    para mostrar en el panel lateral. Incluye leídas y no leídas.
    """
    notificaciones = NotificacionAgente.objects.filter(usuario=request.user).order_by("-creado_en")[
        :30
    ]
    unread_count = NotificacionAgente.objects.filter(usuario=request.user, leida=False).count()
    return render(
        request,
        "core/partials/notif_panel_items.html",
        {"notificaciones": notificaciones, "unread_count": unread_count},
    )


@login_required
@require_POST
def notificaciones_marcar_leidas_view(request):
    """
    Marca todas las notificaciones del usuario como leídas
    y devuelve la lista actualizada para HTMX swap.
    """
    NotificacionAgente.objects.filter(usuario=request.user, leida=False).update(leida=True)
    notificaciones = NotificacionAgente.objects.filter(usuario=request.user).order_by("-creado_en")[
        :30
    ]
    return render(
        request,
        "core/partials/notif_panel_items.html",
        {"notificaciones": notificaciones, "unread_count": 0},
    )


@login_required
def notificaciones_badge_view(request):
    """
    Devuelve el badge del botón de campana con la cantidad de notificaciones no leídas.
    """
    unread_count = NotificacionAgente.objects.filter(usuario=request.user, leida=False).count()
    return render(
        request,
        "core/partials/notif_badge.html",
        {"unread_count": unread_count},
    )

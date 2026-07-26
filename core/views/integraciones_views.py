"""
Vista de Integraciones (API Keys, Webhooks, Notificaciones).
Página unificada para gestionar todas las integraciones del usuario.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View


@method_decorator(login_required, name="dispatch")
class IntegracionesView(View):
    """
    Vista principal de Integraciones.
    Muestra tabs para API Keys, Webhooks y Preferencias de Notificación.
    """

    template_name = "core/integraciones.html"

    def get(self, request):
        """get."""
        context = {
            "active_tab": request.GET.get("tab", "apikeys"),
        }
        return render(request, self.template_name, context)

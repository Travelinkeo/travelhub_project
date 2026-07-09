"""
Widget de chat en vivo (Tawk.to / Crisp).

Renderiza el snippet solo si LIVE_CHAT_PROVIDER y LIVE_CHAT_ID están configurados.
"""

from django.conf import settings
from django.template.loader import render_to_string


def render_chat_widget(request):
    """Renderiza el snippet de chat si está configurado."""
    provider = getattr(settings, "LIVE_CHAT_PROVIDER", "").lower()
    chat_id = getattr(settings, "LIVE_CHAT_ID", "")

    if not provider or not chat_id:
        return ""

    if provider == "tawkto":
        return render_to_string("core/partials/_chat_tawkto.html", {"property_id": chat_id})
    elif provider == "crisp":
        return render_to_string("core/partials/_chat_crisp.html", {"website_id": chat_id})
    return ""

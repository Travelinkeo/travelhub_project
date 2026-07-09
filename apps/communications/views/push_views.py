"""
API de suscripción a notificaciones Push (Web Push).

Permite a los navegadores suscribirse/desuscribirse de notificaciones push.
"""

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.communications.models.push_subscription import PushSubscription


@require_POST
@csrf_exempt
def push_subscribe(request):
    """Registra una suscripción push del navegador."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    endpoint = data.get("endpoint")
    auth_key = data.get("keys", {}).get("auth", "")
    p256dh_key = data.get("keys", {}).get("p256dh", "")

    if not endpoint or not auth_key or not p256dh_key:
        return JsonResponse({"error": "Missing subscription data"}, status=400)

    sub, created = PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "user": request.user,
            "agencia": getattr(request, "agencia", None),
            "auth_key": auth_key,
            "p256dh_key": p256dh_key,
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:512],
            "active": True,
        },
    )

    return JsonResponse({"status": "created" if created else "updated"})


@require_POST
@csrf_exempt
def push_unsubscribe(request):
    """Desuscribe una suscripción push."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    endpoint = data.get("endpoint")
    if endpoint:
        PushSubscription.objects.filter(endpoint=endpoint).update(active=False)

    return JsonResponse({"status": "unsubscribed"})

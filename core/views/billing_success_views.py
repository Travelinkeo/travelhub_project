"""Vistas de éxito/cancelación para Stripe checkout."""
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def billing_success(request):
    """Página de éxito después del pago."""
    session_id = request.GET.get('session_id')
    return render(request, 'billing/success.html', {
        'session_id': session_id,
        'message': '¡Pago exitoso! Tu plan ha sido actualizado.'
    })

@csrf_exempt
def billing_cancel(request):
    """Página de cancelación del pago."""
    return render(request, 'billing/cancel.html', {
        'message': 'Pago cancelado. Puedes intentarlo de nuevo cuando quieras.'
    })

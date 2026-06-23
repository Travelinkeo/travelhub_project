"""Vistas de éxito/cancelación para Stripe checkout."""

import logging

import stripe
from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse

logger = logging.getLogger(__name__)


def billing_success(request):
    """Página de éxito después del pago — verifica con Stripe que el pago fue completado."""
    session_id = request.GET.get("session_id")
    payment_verified = False

    if session_id:
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                payment_verified = True
            else:
                logger.warning(
                    "Stripe session %s payment_status=%s (expected 'paid')",
                    session_id,
                    session.payment_status,
                )
        except stripe.error.StripeError as e:
            logger.error("Error verifying Stripe session %s: %s", session_id, e)
        except Exception as e:
            logger.error("Unexpected error verifying Stripe session %s: %s", session_id, e)

    if not payment_verified:
        return redirect(reverse("billing_cancel"))

    return render(
        request,
        "billing/success.html",
        {
            "session_id": session_id,
            "message": "¡Pago exitoso! Tu plan ha sido actualizado.",
        },
    )


def billing_cancel(request):
    """Página de cancelación del pago."""
    return render(
        request,
        "billing/cancel.html",
        {
            "message": "Pago cancelado. Puedes intentarlo de nuevo cuando quieras.",
        },
    )

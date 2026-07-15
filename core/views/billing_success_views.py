"""Vistas de éxito/cancelación para Stripe checkout."""

import logging

import stripe
from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse

logger = logging.getLogger(__name__)


def billing_success(request):
    """Página de éxito después del pago — verifica con Stripe que el pago fue completado.

    Para flujo onboarding (usuario no autenticado): muestra instrucciones de
    magic link. Para usuarios existentes: redirige al dashboard si el pago
    está verificado.
    """
    session_id = request.GET.get("session_id")
    is_onboarding = not request.user.is_authenticated

    if session_id:
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                metadata = session.get("metadata", {})
                onboarding_flow = metadata.get("onboarding") == "true"

                if request.user.is_authenticated and not onboarding_flow:
                    return redirect("/dashboard/")

                return render(
                    request,
                    "billing/success.html",
                    {
                        "session_id": session_id,
                        "onboarding": onboarding_flow,
                        "email": metadata.get("admin_email", ""),
                    },
                )
            else:
                logger.warning(
                    "Stripe session %s payment_status=%s (expected 'paid')",
                    session_id,
                    session.payment_status,
                )
        except stripe.StripeError as e:
            logger.error("Error verifying Stripe session %s: %s", session_id, e)
        except Exception as e:
            logger.error("Unexpected error verifying Stripe session %s: %s", session_id, e)

    if is_onboarding:
        return render(
            request,
            "billing/success.html",
            {"onboarding": True, "email": ""},
        )

    return redirect(reverse("billing_cancel"))


def billing_cancel(request):
    """Página de cancelación del pago."""
    return render(
        request,
        "billing/cancel.html",
        {
            "message": "Pago cancelado. Puedes intentarlo de nuevo cuando quieras.",
        },
    )

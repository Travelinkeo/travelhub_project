"""
Vistas para facturación y gestión de planes SaaS con Stripe.
"""

import logging

from django.views.decorators.csrf import csrf_exempt

try:
    import stripe
except ImportError:
    stripe = None
import os

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.auth_helpers import internal_auth
from core.security import get_agencia_from_request

try:
    import stripe
except ImportError:
    stripe = None

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from apps.finance.services.stripe_service import StripeService
from core.models.agencia import AgenciaConfiguracion

logger = logging.getLogger(__name__)


def _setup_stripe():
    """Asegura la configuración de Stripe."""
    try:
        import stripe

        stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", os.getenv("STRIPE_SECRET_KEY", ""))
        return bool(stripe.api_key)
    except ImportError:
        return False


STRIPE_AVAILABLE = _setup_stripe()


# Configuración de planes y precios
PLAN_CONFIG = {
    "FREE": {
        "name": "Gratuito (Trial 30 días)",
        "price": 0,
        "stripe_price_id": None,
        "usuarios": 1,
        "ventas": 50,
        "features": [
            "1 usuario",
            "50 ventas/mes",
            "Funcionalidad básica",
            "Soporte por email",
        ],
    },
    "BASIC": {
        "name": "Básico",
        "price": 29,
        "stripe_price_id": os.getenv("STRIPE_PRICE_ID_BASIC", ""),
        "usuarios": 3,
        "ventas": 200,
        "features": [
            "3 usuarios",
            "200 ventas/mes",
            "Todas las funcionalidades",
            "Soporte por email",
            "Reportes básicos",
        ],
    },
    "PRO": {
        "name": "Profesional",
        "price": 99,
        "stripe_price_id": os.getenv("STRIPE_PRICE_ID_PRO", ""),
        "usuarios": 10,
        "ventas": 1000,
        "features": [
            "10 usuarios",
            "1000 ventas/mes",
            "Todas las funcionalidades",
            "Integraciones API",
            "Reportes avanzados",
            "Soporte prioritario",
        ],
    },
    "ENTERPRISE": {
        "name": "Enterprise",
        "price": 299,
        "stripe_price_id": os.getenv("STRIPE_PRICE_ID_ENTERPRISE", ""),
        "usuarios": 999999,
        "ventas": 999999,
        "features": [
            "Usuarios ilimitados",
            "Ventas ilimitadas",
            "Todas las funcionalidades",
            "Servidor dedicado",
            "Personalización",
            "Soporte 24/7",
            "Onboarding personalizado",
        ],
    },
}


@extend_schema(exclude=True)
@api_view(["GET"])
@permission_classes([AllowAny])
def get_plans(request):
    """Obtiene la lista de planes disponibles."""
    return Response(
        {
            "plans": PLAN_CONFIG,
            "stripe_available": _setup_stripe(),
        }
    )


@extend_schema(exclude=True)
@api_view(["GET"])
@internal_auth
@permission_classes([IsAuthenticated])
def get_current_subscription(request):
    """Obtiene la suscripción actual del usuario."""
    try:
        agencia = get_agencia_from_request(request)
        if not agencia:
            return Response({"error": "No perteneces a ninguna agencia"}, status=404)

        plan_info = PLAN_CONFIG.get(agencia.plan, PLAN_CONFIG["FREE"])

        return Response(
            {
                "agencia": {
                    "id": agencia.id,
                    "nombre": agencia.nombre,
                    "es_demo": agencia.es_demo,
                },
                "plan": {
                    "code": agencia.plan,
                    "name": plan_info["name"],
                    "price": plan_info["price"],
                    "features": plan_info["features"],
                },
                "usage": {
                    "usuarios": {
                        "usado": agencia.usuarios.filter(activo=True).count(),
                        "limite": agencia.limite_usuarios,
                    },
                    "ventas": {
                        "usado": agencia.ventas_mes_actual,
                        "limite": agencia.limite_ventas_mes,
                    },
                },
                "stripe": {
                    "customer_id": agencia.stripe_customer_id,
                    "subscription_id": agencia.stripe_subscription_id,
                },
                "dates": {
                    "inicio_plan": agencia.fecha_inicio_plan,
                    "fin_trial": agencia.fecha_fin_trial,
                },
            }
        )
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@extend_schema(exclude=True)
@api_view(["POST"])
@internal_auth
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """Crea una sesión de checkout de Stripe."""
    if not _setup_stripe():
        return Response(
            {"error": "Stripe no está configurado. Contacta al administrador."}, status=503
        )

    plan = request.data.get("plan")
    if plan not in PLAN_CONFIG or plan == "FREE":
        return Response({"error": "Plan inválido"}, status=400)

    try:
        agencia = get_agencia_from_request(request)
        if not agencia:
            return Response({"error": "No perteneces a ninguna agencia"}, status=404)

        plan_config = PLAN_CONFIG[plan]
        price_id = plan_config["stripe_price_id"]

        if not price_id:
            return Response(
                {"error": "El plan seleccionado no tiene un ID de precio configurado"}, status=400
            )

        success_url = (
            request.build_absolute_uri("/billing/success/") + "?session_id={CHECKOUT_SESSION_ID}"
        )
        cancel_url = request.build_absolute_uri("/billing/cancel/")

        checkout_url = StripeService.create_checkout_session(
            agencia=agencia, price_id=price_id, success_url=success_url, cancel_url=cancel_url
        )

        # Como StripeService retorna URL string (en mi impl, oops I returned session.url directly)
        # Wait, StripeService.create_checkout_session returns session.url (string)

        return Response(
            {
                "checkout_url": checkout_url,
            }
        )

    except Exception as e:
        return Response({"error": str(e)}, status=500)


@extend_schema(exclude=True)
@api_view(["POST"])
@internal_auth
@permission_classes([IsAuthenticated])
def create_portal_session(request):
    """Crea una sesión del Portal de Clientes de Stripe."""
    if not _setup_stripe():
        return Response({"error": "Stripe no configurado"}, status=503)

    try:
        agencia = get_agencia_from_request(request)
        if not agencia:
            return Response({"error": "No perteneces a ninguna agencia"}, status=404)

        if not agencia.stripe_customer_id:
            return Response({"error": "No eres cliente de Stripe aún"}, status=400)

        return_url = request.build_absolute_uri("/dashboard/modern/")  # O donde sea

        portal_url = StripeService.create_portal_session(agencia, return_url)

        return Response({"portal_url": portal_url})

    except Exception as e:
        return Response({"error": str(e)}, status=500)


@extend_schema(exclude=True)
@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt  # CSRF exempt: secured by Stripe signature verification below
def stripe_webhook(request):
    """Webhook para eventos de Stripe."""
    if not _setup_stripe():
        return Response({"error": "Stripe no configurado"}, status=503)

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        return Response({"error": "Invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError:
        return Response({"error": "Invalid signature"}, status=400)

    try:
        from core.middleware import system_context

        with system_context():
            StripeService.handle_webhook(event)
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        return Response({"error": str(e)}, status=500)

    return Response({"status": "success"})


@extend_schema(exclude=True)
@api_view(["POST"])
@internal_auth
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """Cancela la suscripción actual."""
    if not _setup_stripe():
        return Response({"error": "Stripe no configurado"}, status=503)

    try:
        agencia = get_agencia_from_request(request)
        if not agencia:
            return Response({"error": "No perteneces a ninguna agencia"}, status=404)

        if not agencia.stripe_subscription_id:
            return Response({"error": "No tienes suscripción activa"}, status=400)

        # Cancelar en Stripe
        stripe.Subscription.delete(agencia.stripe_subscription_id)

        # Actualizar agencia
        agencia.plan = "FREE"
        agencia.stripe_subscription_id = ""
        agencia.actualizar_limites_por_plan()
        agencia.save()

        return Response({"message": "Suscripción cancelada exitosamente", "plan": "FREE"})

    except Exception as e:
        return Response({"error": str(e)}, status=500)


@method_decorator(login_required, name="dispatch")
class AccountBillingView(View):
    """Página de facturación y suscripción del usuario."""

    template_name = "core/account_billing.html"

    def get(self, request):
        user = request.user
        agencia = self._get_user_agency(user)

        if not agencia:
            return render(request, self.template_name, {"error": "No tienes una agencia asignada."})

        config = agencia.configuracion
        plan_name = config.plan
        plan_limits = settings.SAAS_PLAN_LIMITS.get(plan_name, settings.SAAS_PLAN_LIMITS["FREE"])
        plan_display = self._plan_display_name(plan_name)

        # Usage stats
        usage = {
            "users": AgenciaConfiguracion.objects.filter(agencia=agencia).count(),
            "ventas_mes": config.ventas_mes_actual,
            "limite_usuarios": config.limite_usuarios,
            "limite_ventas_mes": config.limite_ventas_mes,
        }

        # Trial info
        trial_days_left = None
        if config.plan_status == "trial" and config.fecha_fin_trial:
            from datetime import date

            delta = config.fecha_fin_trial - date.today()
            trial_days_left = max(delta.days, 0)

        # Stripe portal link (if they have a Stripe customer)
        stripe_portal_url = None
        if agencia.stripe_customer_id:
            try:
                session = StripeService.create_portal_session(
                    agencia,
                    return_url=request.build_absolute_uri(reverse("account_billing")),
                )
                stripe_portal_url = session.url
            except Exception as e:
                logger.warning(f"Stripe portal session error: {e}")

        # Available plans for upgrade
        plans = self._get_available_plans(plan_name)

        return render(
            request,
            self.template_name,
            {
                "agencia": agencia,
                "config": config,
                "plan_name": plan_name,
                "plan_display": plan_display,
                "plan_limits": plan_limits,
                "usage": usage,
                "trial_days_left": trial_days_left,
                "stripe_portal_url": stripe_portal_url,
                "plans": plans,
                "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            },
        )

    def post(self, request):
        """Handle upgrade/downgrade actions."""
        action = request.POST.get("action")
        agencia = self._get_user_agency(request.user)

        if not agencia:
            return redirect("account_billing")

        if action == "upgrade":
            price_id = request.POST.get("price_id")
            if price_id:
                try:
                    session = StripeService.create_checkout_session(
                        agencia=agencia,
                        price_id=price_id,
                        success_url=request.build_absolute_uri(reverse("account_billing")),
                        cancel_url=request.build_absolute_uri(reverse("account_billing")),
                    )
                    return redirect(session.url)
                except Exception as e:
                    logger.error(f"Checkout session error: {e}")
                    return render(
                        request,
                        self.template_name,
                        {
                            "error": f"Error al iniciar el pago: {e}",
                        },
                    )

        return redirect("account_billing")

    @staticmethod
    def _get_user_agency(user):
        """Obtiene la primera agencia del usuario."""
        ua = user.agencias.select_related("agencia__configuracion").first()
        return ua.agencia if ua else None

    @staticmethod
    def _plan_display_name(plan):
        names = {
            "FREE": "Gratuito",
            "BASIC": "Básico",
            "PRO": "Profesional",
            "ENTERPRISE": "Enterprise",
        }
        return names.get(plan, plan)

    @staticmethod
    def _get_available_plans(current_plan):
        """Planes disponibles para upgrade, con sus precios desde settings."""
        order = ["FREE", "BASIC", "PRO", "ENTERPRISE"]
        plans = []
        for name in order:
            limits = settings.SAAS_PLAN_LIMITS.get(name, {})
            price_id = settings.STRIPE_PRICE_IDS.get(name, "")
            plans.append(
                {
                    "name": name,
                    "display": {
                        "FREE": "Gratuito",
                        "BASIC": "Básico",
                        "PRO": "Profesional",
                        "ENTERPRISE": "Enterprise",
                    }[name],
                    "limits": limits,
                    "price_id": price_id if name != "FREE" else None,
                    "is_current": name == current_plan,
                    "is_upgrade": order.index(name) > order.index(current_plan),
                }
            )
        return plans

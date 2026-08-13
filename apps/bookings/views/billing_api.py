"""
apps/bookings/views/billing_api.py
===================================
Endpoints de la API REST para Onboarding de Agencias (Self-Service) y Facturación/Suscripción SaaS.
"""

import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api import SuscripcionService, get_current_agency

logger = logging.getLogger(__name__)


class RegisterTenantAPIView(APIView):
    """
    Endpoint Público para el autoregistro (Self-Service Onboarding) de nuevas Agencias de Viajes.
    No requiere autenticación previa.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data
        nombre_agencia = data.get("nombre_agencia")
        email_propietario = data.get("email_propietario")
        password = data.get("password")
        plan = data.get("plan", "FREE")
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        telefono = data.get("telefono", "")
        subdominio_slug = data.get("subdominio_slug", "")

        if not nombre_agencia or not email_propietario or not password:
            return Response(
                {
                    "error": "Los campos 'nombre_agencia', 'email_propietario' y 'password' son obligatorios."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            agencia, user = SuscripcionService.register_new_tenant(
                nombre_agencia=nombre_agencia,
                email_propietario=email_propietario,
                password=password,
                first_name=first_name,
                last_name=last_name,
                plan=plan,
                telefono=telefono,
                subdominio_slug=subdominio_slug,
            )

            return Response(
                {
                    "message": f"Agencia '{agencia.nombre}' registrada exitosamente en TravelHub.",
                    "agencia_id": agencia.id,
                    "agencia_nombre": agencia.nombre,
                    "plan": agencia.plan,
                    "propietario_username": user.username,
                    "email": user.email,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.exception("Error en registro self-service de agencia: %s", e)
            return Response(
                {"error": f"No se pudo completar el registro: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CurrentBillingPlanAPIView(APIView):
    """
    Endpoint Autenticado para consultar el plan actual, consumo de ventas/boletos y límites SaaS de la agencia.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        agencia = get_current_agency()
        if not agencia:
            return Response(
                {"error": "No hay un contexto de agencia asociado a esta solicitud."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        config = getattr(agencia, "configuracion", None)
        plan_name = config.plan if config else "FREE"
        limite_ventas = config.limite_ventas_mes if config else 50
        ventas_actuales = config.ventas_mes_actual if config else 0
        plan_status = config.plan_status if config else "active"

        porcentaje_uso = (
            round((ventas_actuales / limite_ventas) * 100, 1) if limite_ventas > 0 else 100.0
        )

        return Response(
            {
                "agencia_id": agencia.id,
                "agencia_nombre": agencia.nombre,
                "plan": plan_name,
                "plan_status": plan_status,
                "limite_ventas_mes": limite_ventas,
                "ventas_mes_actual": ventas_actuales,
                "ventas_disponibles": max(0, limite_ventas - ventas_actuales),
                "porcentaje_uso": porcentaje_uso,
                "limite_usuarios": config.limite_usuarios if config else 1,
                "subdominio_slug": config.subdominio_slug if config else "",
                "stripe_customer_id": config.stripe_customer_id if config else "",
            },
            status=status.HTTP_200_OK,
        )


class CheckoutPlanAPIView(APIView):
    """
    Endpoint Autenticado para realizar Checkout/Upgrade de Plan SaaS (Stripe / PagoMóvil / Zelle).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        agencia = get_current_agency()
        if not agencia:
            return Response(
                {"error": "No hay un contexto de agencia asociado a esta solicitud."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_plan = request.data.get("new_plan", "PRO")
        metodo_pago = request.data.get("metodo_pago", "stripe")  # stripe, zelle, pagomovil
        referencia_pago = request.data.get("referencia_pago", "")

        try:
            config = SuscripcionService.upgrade_plan(
                agencia=agencia,
                new_plan=new_plan,
                stripe_customer_id=f"cus_simulated_{agencia.id}" if metodo_pago == "stripe" else "",
                stripe_subscription_id=f"sub_simulated_{agencia.id}"
                if metodo_pago == "stripe"
                else "",
            )

            return Response(
                {
                    "message": f"Plan de la agencia actualizado a '{config.plan}' con éxito.",
                    "plan": config.plan,
                    "plan_status": config.plan_status,
                    "limite_ventas_mes": config.limite_ventas_mes,
                    "limite_usuarios": config.limite_usuarios,
                    "metodo_pago_registrado": metodo_pago,
                    "referencia_pago": referencia_pago,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Error en checkout/upgrade de plan: %s", e)
            return Response(
                {"error": f"Error al procesar la suscripción: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

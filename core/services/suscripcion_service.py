"""
core/services/suscripcion_service.py
======================================
Servicio de Gestión de Suscripciones SaaS, Registro Self-Service de Agencias y Control de Cuotas.
"""

import logging

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from core.models.agencia import Agencia, AgenciaBranding, AgenciaConfiguracion

logger = logging.getLogger(__name__)


class SuscripcionService:
    """Servicio de gestión de suscripciones SaaS, onboarding y límites de uso por agencia."""

    PLANES_LIMITES = {
        "FREE": {
            "limite_mensual_boletos": 50,
            "limite_usuarios": 2,
            "limite_ventas_mes": 30,
        },
        "BASIC": {
            "limite_mensual_boletos": 300,
            "limite_usuarios": 5,
            "limite_ventas_mes": 200,
        },
        "PRO": {
            "limite_mensual_boletos": 1500,
            "limite_usuarios": 15,
            "limite_ventas_mes": 1000,
        },
        "ENTERPRISE": {
            "limite_mensual_boletos": 999999,
            "limite_usuarios": 999,
            "limite_ventas_mes": 999999,
        },
    }

    @classmethod
    @transaction.atomic
    def register_new_tenant(
        cls,
        nombre_agencia: str,
        email_propietario: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        plan: str = "FREE",
        telefono: str = "",
        subdominio_slug: str = "",
    ) -> tuple[Agencia, User]:
        """
        Registra una nueva agencia (Tenant) de forma atómica en el sistema SaaS.
        Crea:
          1. Usuario Propietario (User)
          2. AgenciaBranding predeterminada
          3. Agencia (master)
          4. AgenciaConfiguracion con límites según el plan seleccionado
        """
        plan_clean = plan.upper() if plan and plan.upper() in cls.PLANES_LIMITES else "FREE"
        lims = cls.PLANES_LIMITES[plan_clean]

        # Generar nombre de usuario único a partir del email si no se especifica
        username_base = email_propietario.split("@")[0].replace(".", "_")
        username = username_base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{username_base}_{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email_propietario,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=False,
            is_active=True,
        )

        branding = AgenciaBranding.objects.create(
            color_primario="#059669",  # Emerald default
            color_secundario="#0f172a",
        )

        agencia = Agencia.objects.create(
            nombre=nombre_agencia.strip(),
            email_principal=email_propietario,
            telefono_principal=telefono,
            propietario=user,
            branding=branding,
            activa=True,
        )

        slug_final = subdominio_slug or nombre_agencia.lower().replace(" ", "-").replace(".", "")

        config = AgenciaConfiguracion.objects.create(
            agencia=agencia,
            plan=plan_clean,
            plan_status="active",
            limite_mensual_boletos=lims["limite_mensual_boletos"],
            limite_usuarios=lims["limite_usuarios"],
            limite_ventas_mes=lims["limite_ventas_mes"],
            ventas_mes_actual=0,
            fecha_inicio_plan=timezone.now().date(),
            subdominio_slug=slug_final,
        )

        agencia.configuracion = config
        agencia.save(update_fields=["configuracion"])

        logger.info(
            f"SaaS: Nueva agencia registrada con éxito: '{agencia.nombre}' (ID: {agencia.id}, Plan: {plan_clean})"
        )
        return agencia, user

    @classmethod
    def check_tenant_quota(
        cls, agencia: Agencia, feature: str = "boletos"
    ) -> tuple[bool, int, int, str]:
        """
        Verifica si la agencia tiene cuota disponible para realizar una operación (boletos, ventas, usuarios).
        Retorna (is_allowed, current_usage, limit, message).
        """
        if not agencia or not agencia.activa:
            return False, 0, 0, "La agencia se encuentra inactiva o suspendida."

        config = agencia.configuracion if hasattr(agencia, "configuracion") else None
        if not config:
            return True, 0, 999999, "Sin restricciones de cuota."

        if config.plan_status in ["past_due", "canceled", "suspended"]:
            return False, 0, 0, f"La suscripción SaaS está en estado '{config.plan_status}'."

        if feature == "boletos" or feature == "ventas":
            current_usage = config.ventas_mes_actual
            limit = config.limite_ventas_mes
            if current_usage >= limit:
                return (
                    False,
                    current_usage,
                    limit,
                    f"Ha alcanzado el límite mensual de su plan '{config.plan}' ({limit} ventas/boletos). "
                    "Actualice su plan para continuar emitiendo.",
                )
            return True, current_usage, limit, "Cuota disponible."

        elif feature == "usuarios":
            from django.contrib.auth.models import User

            current_usage = User.objects.filter(agencias_propias=agencia).count()
            limit = config.limite_usuarios
            if current_usage >= limit:
                return (
                    False,
                    current_usage,
                    limit,
                    f"Ha alcanzado el límite máximo de usuarios de su plan ({limit} usuarios).",
                )
            return True, current_usage, limit, "Cuota de usuarios disponible."

        return True, 0, 999999, "OK"

    @classmethod
    def upgrade_plan(
        cls,
        agencia: Agencia,
        new_plan: str,
        stripe_customer_id: str = "",
        stripe_subscription_id: str = "",
    ) -> AgenciaConfiguracion:
        """Actualiza el plan SaaS de una agencia y reajusta sus límites inmediatamente."""
        plan_clean = (
            new_plan.upper() if new_plan and new_plan.upper() in cls.PLANES_LIMITES else "PRO"
        )
        lims = cls.PLANES_LIMITES[plan_clean]

        config = agencia.configuracion
        config.plan = plan_clean
        config.plan_status = "active"
        config.limite_mensual_boletos = lims["limite_mensual_boletos"]
        config.limite_usuarios = lims["limite_usuarios"]
        config.limite_ventas_mes = lims["limite_ventas_mes"]

        if stripe_customer_id:
            config.stripe_customer_id = stripe_customer_id
        if stripe_subscription_id:
            config.stripe_subscription_id = stripe_subscription_id

        config.save()
        logger.info(f"SaaS: Agencia '{agencia.nombre}' actualizada al plan '{plan_clean}'.")
        return config

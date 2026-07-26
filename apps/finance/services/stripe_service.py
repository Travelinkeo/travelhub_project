import logging
from datetime import UTC

import stripe
from django.conf import settings
from django.core.cache import cache

from core.api import Agencia, UsuarioAgencia

logger = logging.getLogger(__name__)


class StripeService:
    """StripeService."""

    @staticmethod
    def _ensure_stripe_key():
        stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")

    @staticmethod
    def create_checkout_session(agencia, price_id, success_url, cancel_url):
        StripeService._ensure_stripe_key()

        if not agencia.stripe_customer_id:
            customer = stripe.Customer.create(
                email=agencia.email_principal,
                name=agencia.nombre,
                metadata={"agencia_id": agencia.id},
            )
            agencia.stripe_customer_id = customer.id
            agencia.save(update_fields=["stripe_customer_id"])

        session = stripe.checkout.Session.create(
            customer=agencia.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "agencia_id": agencia.id,
            },
        )
        return session.url

    @staticmethod
    def create_portal_session(agencia, return_url):
        StripeService._ensure_stripe_key()
        if not agencia.stripe_customer_id:
            raise ValueError("La agencia no tiene un Stripe Customer ID asociado.")

        session = stripe.billing_portal.Session.create(
            customer=agencia.stripe_customer_id,
            return_url=return_url,
        )
        return session.url

    @staticmethod
    def handle_webhook(event):
        StripeService._ensure_stripe_key()
        evt_type = event["type"]

        event_id = event.get("id", "")
        idempotency_key = f"stripe_webhook:{event_id}"
        if cache.get(idempotency_key):
            logger.info("Duplicate webhook event %s ignored", event_id)
            return

        cache.set(idempotency_key, True, 86400)

        if evt_type == "checkout.session.completed":
            session = event["data"]["object"]
            metadata = session.get("metadata", {})

            if metadata.get("onboarding") == "true":
                auth_method = metadata.get("auth_method", "password")
                StripeService._provision_new_agency(session, auth_method=auth_method)
            else:
                agencia_id = metadata.get("agencia_id")
                plan = metadata.get("plan")
                if agencia_id and plan:
                    StripeService._update_agencia_plan(
                        agencia_id, plan, session.get("subscription")
                    )

        elif evt_type == "customer.subscription.deleted":
            StripeService._handle_subscription_deleted(event["data"]["object"])

        elif evt_type == "invoice.payment_succeeded":
            StripeService._handle_invoice_payment(event["data"]["object"], status="active")

        elif evt_type == "invoice.payment_failed":
            StripeService._handle_invoice_payment(event["data"]["object"], status="past_due")

    @staticmethod
    def _provision_new_agency(session, auth_method="password"):
        from django.contrib.auth.models import User

        metadata = session.get("metadata", {})
        admin_email = metadata.get("admin_email")
        agency_name = metadata.get("agency_name")
        subdomain = metadata.get("subdomain")
        brand_color = metadata.get("brand_color", "#3b82f6")
        plan = metadata.get("plan", "BASIC")
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")

        if not admin_email or not agency_name or not subdomain:
            logger.error(
                "Missing required metadata in Stripe checkout session %s", session.get("id")
            )
            return

        idempotency_key = f"provision_agency:{subdomain}"
        if cache.get(idempotency_key):
            logger.info("Agency %s already provisioned, skipping", subdomain)
            return

        agencia, agencia_created = Agencia.objects.get_or_create(
            subdominio_slug=subdomain,
            defaults={
                "nombre": agency_name,
                "email_principal": admin_email,
                "color_primario": brand_color,
                "plan": plan,
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription_id,
                "plan_status": "active",
            },
        )

        if not agencia_created:
            agencia.stripe_customer_id = customer_id
            agencia.stripe_subscription_id = subscription_id
            agencia.save()

        user, user_created = User.objects.get_or_create(
            email=admin_email,
            defaults={
                "username": admin_email,
                "is_active": True,
            },
        )

        if auth_method == "magic_link" or not metadata.get("admin_password"):
            user.set_unusable_password()
        elif user_created and metadata.get("admin_password"):
            user.set_password(metadata["admin_password"])

        user.save()

        UsuarioAgencia.objects.get_or_create(
            usuario=user, agencia=agencia, defaults={"rol": "admin"}
        )

        if not agencia.propietario:
            agencia.propietario = user
            agencia.save()

        agencia.actualizar_limites_por_plan()

        try:
            from apps.common.services.magic_link_service import (
                create_magic_link,
                send_magic_link_email,
            )

            token = create_magic_link(admin_email, redirect_url="/dashboard/", is_onboarding=False)
            send_magic_link_email(token)
        except Exception as e:
            logger.warning("Could not send magic link welcome email to %s: %s", admin_email, e)

        try:
            from apps.common.tasks import enviar_bienvenida_agencia_task

            enviar_bienvenida_agencia_task.delay(agencia.pk, user.pk)
        except Exception as e:
            logger.warning("Could not queue welcome email to %s: %s", admin_email, e)

        cache.set(idempotency_key, True, 86400)
        logger.info(
            "Agency provisioned: %s (%s) plan=%s auth=%s", agency_name, subdomain, plan, auth_method
        )

    @staticmethod
    def _update_agencia_plan(agencia_id, plan, subscription_id):
        try:
            agencia = Agencia.objects.get(id=agencia_id)
            agencia.plan = plan
            agencia.stripe_subscription_id = subscription_id
            agencia.plan_status = "active"
            agencia.actualizar_limites_por_plan()
            agencia.save()
        except Agencia.DoesNotExist:
            logger.warning("Agencia %s not found for plan update", agencia_id)

    @staticmethod
    def _handle_subscription_deleted(subscription):
        try:
            agencia = Agencia.objects.get(stripe_subscription_id=subscription["id"])
            agencia.plan = "FREE"
            agencia.plan_status = "canceled"
            agencia.stripe_subscription_id = ""
            agencia.actualizar_limites_por_plan()
            agencia.save()
        except Agencia.DoesNotExist:
            pass

    @staticmethod
    def _handle_invoice_payment(invoice, status):
        subscription_id = invoice.get("subscription")
        if not subscription_id:
            return

        try:
            agencia = Agencia.objects.get(stripe_subscription_id=subscription_id)
            agencia.plan_status = status
            if "lines" in invoice and invoice["lines"]["data"]:
                period_end = invoice["lines"]["data"][0]["period"]["end"]
                from datetime import datetime

                agencia.subscription_end_date = datetime.fromtimestamp(period_end, tz=UTC)
            agencia.save(update_fields=["plan_status", "subscription_end_date"])
        except Agencia.DoesNotExist:
            pass

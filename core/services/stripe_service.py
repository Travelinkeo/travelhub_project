import stripe
from django.conf import settings
from django.urls import reverse
from core.models.agencia import Agencia

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    @staticmethod
    def create_checkout_session(agencia: Agencia, price_id: str, success_url: str, cancel_url: str):
        """Crea una sesión de Checkout para suscripción."""
        
        # 1. Crear o recuperar Customer
        if not agencia.stripe_customer_id:
            customer = stripe.Customer.create(
                email=agencia.email_principal,
                name=agencia.nombre,
                metadata={'agencia_id': agencia.id}
            )
            agencia.stripe_customer_id = customer.id
            agencia.save(update_fields=['stripe_customer_id'])
        
        # 2. Crear sesión
        session = stripe.checkout.Session.create(
            customer=agencia.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'agencia_id': agencia.id,
                'plan': next(k for k, v in settings.STRIPE_PRICE_IDS.items() if v == price_id)
            }
        )
        return session.url

    @staticmethod
    def create_portal_session(agencia: Agencia, return_url: str):
        """Crea una sesión del Portal de Clientes."""
        if not agencia.stripe_customer_id:
            raise ValueError("La agencia no tiene un Stripe Customer ID asociado.")
            
        session = stripe.billing_portal.Session.create(
            customer=agencia.stripe_customer_id,
            return_url=return_url,
        )
        return session.url

    @staticmethod
    def handle_webhook(event):
        """Maneja eventos de Webhook de Stripe."""
        evt_type = event['type']
        
        if evt_type == 'checkout.session.completed':
            session = event['data']['object']
            agencia_id = session.get('metadata', {}).get('agencia_id')
            plan = session.get('metadata', {}).get('plan')
            
            if agencia_id and plan:
                StripeService._update_agencia_plan(agencia_id, plan, session.get('subscription'))

        elif evt_type == 'customer.subscription.deleted':
            subscription = event['data']['object']
            StripeService._handle_subscription_deleted(subscription)

        elif evt_type == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            StripeService._handle_invoice_payment(invoice, status='active')

        elif evt_type == 'invoice.payment_failed':
            invoice = event['data']['object']
            StripeService._handle_invoice_payment(invoice, status='past_due')

    @staticmethod
    def _update_agencia_plan(agencia_id, plan, subscription_id):
        try:
            agencia = Agencia.objects.get(id=agencia_id)
            agencia.plan = plan
            agencia.stripe_subscription_id = subscription_id
            agencia.plan_status = 'active'
            agencia.actualizar_limites_por_plan()
            agencia.save()
        except Agencia.DoesNotExist:
            pass

    @staticmethod
    def _handle_subscription_deleted(subscription):
        try:
            agencia = Agencia.objects.get(stripe_subscription_id=subscription['id'])
            agencia.plan = 'FREE'
            agencia.plan_status = 'canceled'
            agencia.stripe_subscription_id = ''
            agencia.actualizar_limites_por_plan()
            agencia.save()
        except Agencia.DoesNotExist:
            pass

    @staticmethod
    def _handle_invoice_payment(invoice, status):
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return
            
        try:
            agencia = Agencia.objects.get(stripe_subscription_id=subscription_id)
            agencia.plan_status = status
            # Actualizar fecha fin si está disponible en period_end
            if 'lines' in invoice and invoice['lines']['data']:
                period_end = invoice['lines']['data'][0]['period']['end']
                from datetime import datetime, timezone
                agencia.subscription_end_date = datetime.fromtimestamp(period_end, tz=timezone.utc)
            agencia.save(update_fields=['plan_status', 'subscription_end_date'])
        except Agencia.DoesNotExist:
            pass

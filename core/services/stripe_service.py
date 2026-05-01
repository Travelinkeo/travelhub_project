import stripe
from django.conf import settings
from django.urls import reverse
from core.models.agencia import Agencia

class StripeService:
    @staticmethod
    def _ensure_stripe_key():
        """Asegura que la API Key esté configurada (Lazy Load)"""
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

    @staticmethod
    def create_checkout_session(agencia: Agencia, price_id: str, success_url: str, cancel_url: str):
        """Crea una sesión de Checkout para suscripción."""
        StripeService._ensure_stripe_key()
        
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
        """Maneja eventos de Webhook de Stripe."""
        StripeService._ensure_stripe_key()
        evt_type = event['type']
        
        if evt_type == 'checkout.session.completed':
            session = event['data']['object']
            metadata = session.get('metadata', {})
            
            # Caso 1: Nuevo Onboarding SaaS (Registro Público)
            if metadata.get('onboarding') == 'true':
                StripeService._provision_new_agency(session)
            
            # Caso 2: Upgrade de Plan (Cliente existente)
            else:
                agencia_id = metadata.get('agencia_id')
                plan = metadata.get('plan')
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
    def _provision_new_agency(session):
        """Crea la Agencia y el Administrador principal tras el pago inicial."""
        from django.contrib.auth.models import User
        from core.models.agencia import Agencia, UsuarioAgencia
        import stripe
        
        metadata = session.get('metadata', {})
        admin_email = metadata.get('admin_email')
        admin_pass = metadata.get('admin_password')
        agency_name = metadata.get('agency_name')
        subdomain = metadata.get('subdomain')
        brand_color = metadata.get('brand_color')
        plan = metadata.get('plan', 'BASIC')
        subscription_id = session.get('subscription')
        customer_id = session.get('customer')

        # 1. Crear Agencia
        agencia, created = Agencia.objects.get_or_create(
            subdominio_slug=subdomain,
            defaults={
                'nombre': agency_name,
                'email_principal': admin_email,
                'color_primario': brand_color,
                'plan': plan,
                'stripe_customer_id': customer_id,
                'stripe_subscription_id': subscription_id,
                'plan_status': 'active'
            }
        )
        
        if not created:
            # Si ya existía, actualizamos datos de Stripe
            agencia.stripe_customer_id = customer_id
            agencia.stripe_subscription_id = subscription_id
            agencia.save()

        # 2. Crear Usuario Administrador (Si no existe)
        user, u_created = User.objects.get_or_create(
            email=admin_email,
            defaults={
                'username': admin_email,
                'first_name': metadata.get('admin_name', 'Admin'),
            }
        )
        if u_created:
            user.set_password(admin_pass)
            user.save()

        # 3. Vincular Usuario a Agencia como Admin
        UsuarioAgencia.objects.get_or_create(
            usuario=user,
            agencia=agencia,
            defaults={'rol': 'admin'}
        )
        
        # 4. Actualizar Propietario de la Agencia
        if not agencia.propietario:
            agencia.propietario = user
            agencia.save()
        
        # 5. Configurar límites iniciales
        agencia.actualizar_limites_por_plan()
        
        # 6. Enviar Email de Bienvenida
        from core.services.notification_service import NotificationService
        NotificationService.enviar_bienvenida_agencia(agencia, user)
        
        print(f"🚀 AGENCIA PROVISIONADA: {agency_name} ({subdomain})")

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

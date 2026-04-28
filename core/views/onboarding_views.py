import json
import stripe
import logging
from django.conf import settings
from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Agencia

logger = logging.getLogger(__name__)

class SaaSOnboardingView(View):
    """
    Vista pública para el registro de agencias (B2B SaaS Onboarding).
    """
    template_name = "onboarding/b2b_onboarding.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        # Configurar API Key de forma segura
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        # 1. Extraer datos del formulario Alpine.js
        admin_email = request.POST.get('admin_email')
        admin_password = request.POST.get('admin_password')
        agency_name = request.POST.get('agency_name')
        subdomain = request.POST.get('subdomain')
        plan = request.POST.get('plan') # BASIC, PRO, ENTERPRISE
        brand_color = request.POST.get('brand_color', '#3b82f6')
        
        # 2. Validaciones Previas (Evitar duplicados antes de Stripe)
        if User.objects.filter(email=admin_email).exists():
            return HttpResponse("El email ya está registrado.", status=400)
        
        if Agencia.objects.filter(subdominio_slug=subdomain).exists():
            return HttpResponse("El subdominio ya está en uso.", status=400)

        # 3. Mapeo de Precios Stripe (DUMMY IDs por ahora)
        # En producción estos IDs vienen de la consola de Stripe
        STRIPE_PRICES = {
            'BASIC': 'price_starter_29',
            'PRO': 'price_pro_99',
            'ENTERPRISE': 'price_ent_299'
        }
        price_id = STRIPE_PRICES.get(plan, STRIPE_PRICES['BASIC'])

        # 4. Crear Sesión de Checkout de Stripe
        try:
            # Empaquetamos los datos en metadata para recuperarlos en el Webhook
            metadata = {
                'admin_email': admin_email,
                'admin_password': admin_password,
                'agency_name': agency_name,
                'subdomain': subdomain,
                'brand_color': brand_color,
                'plan': plan,
                'onboarding': 'true'
            }

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f"TravelHub ERP - Plan {plan}",
                            'description': f"Suscripción mensual para {agency_name}",
                        },
                        'unit_amount': 2900 if plan == 'BASIC' else (9900 if plan == 'PRO' else 29900),
                        'recurring': {'interval': 'month'},
                    },
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=request.build_absolute_uri('/') + '?status=success',
                cancel_url=request.build_absolute_uri('/') + '?status=cancel',
                customer_email=admin_email,
                metadata=metadata
            )
            
            return redirect(checkout_session.url, code=303)

        except Exception as e:
            logger.error(f"Error SaaSOnboardingView Stripe: {e}")
            return HttpResponse(f"Error al iniciar el pago: {str(e)}", status=500)

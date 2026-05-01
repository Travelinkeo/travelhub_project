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

from core.views.billing_views import PLAN_CONFIG

class SaaSOnboardingView(View):
    """
    Vista pública para el registro de agencias (B2B SaaS Onboarding).
    """
    template_name = "onboarding/b2b_onboarding.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        # 1. Extraer datos del formulario Alpine.js
        admin_email = request.POST.get('admin_email')
        admin_password = request.POST.get('admin_password')
        agency_name = request.POST.get('agency_name')
        subdomain = request.POST.get('subdomain')
        plan = request.POST.get('plan', 'BASIC')
        brand_color = request.POST.get('brand_color', '#3b82f6')
        
        # 2. Validaciones Previas
        if User.objects.filter(email=admin_email).exists():
            return render(request, self.template_name, {'error': "El email ya está registrado."})
        
        if Agencia.objects.filter(subdominio_slug=subdomain).exists():
            return render(request, self.template_name, {'error': "El subdominio ya está en uso."})

        # 3. Mapeo de Precios desde PLAN_CONFIG
        plan_data = PLAN_CONFIG.get(plan, PLAN_CONFIG['BASIC'])
        price_id = plan_data.get('stripe_price_id')

        # 4. Caso Especial: FREE / TRIAL (Sin Stripe Checkout inmediato si se desea)
        # Por ahora, todos pasan por Stripe para validar tarjeta, pero si es FREE
        # podríamos provisionar directamente. El plan dice "TRIAL 30 días".
        
        if not price_id and plan != 'FREE':
            return HttpResponse("Error de configuración de precios. Contacte soporte.", status=500)

        # 5. Crear Sesión de Checkout de Stripe
        try:
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
                    'price': price_id,
                    'quantity': 1,
                }] if price_id else [{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f"TravelHub ERP - Plan {plan} (Trial)",
                        },
                        'unit_amount': 0,
                        'recurring': {'interval': 'month'},
                    },
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=request.build_absolute_uri(reverse('billing_success')) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=request.build_absolute_uri(reverse('billing_cancel')),
                customer_email=admin_email,
                metadata=metadata
            )
            
            return redirect(checkout_session.url, code=303)

        except Exception as e:
            logger.error(f"Error SaaSOnboardingView Stripe: {e}")
            return render(request, self.template_name, {'error': f"Error al iniciar el pago: {str(e)}"})

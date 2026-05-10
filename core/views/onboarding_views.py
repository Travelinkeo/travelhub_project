import json
import logging
import time
from django.conf import settings
from django.contrib.auth import login, get_user_model
from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from django.urls import reverse
from django.core.cache import cache

from core.models.agencia import Agencia, UsuarioAgencia
from core.views.billing_views import PLAN_CONFIG

logger = logging.getLogger(__name__)
User = get_user_model()

MAGIC_LINK_RATE_LIMIT_SECONDS = 60
MAGIC_LINK_RATE_LIMIT_MAX = 5


def check_rate_limit(ip_address):
    cache_key = f'magic_link_rate:{ip_address}'
    attempts = cache.get(cache_key, [])
    now = time.time()
    attempts = [t for t in attempts if now - t < MAGIC_LINK_RATE_LIMIT_SECONDS * 60]
    if len(attempts) >= MAGIC_LINK_RATE_LIMIT_MAX:
        return False
    attempts.append(now)
    cache.set(cache_key, attempts, MAGIC_LINK_RATE_LIMIT_SECONDS * 60)
    return True


class MagicLinkRequestView(View):
    def post(self, request):
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', '')
        if not check_rate_limit(ip_address):
            return JsonResponse({'error': 'Demasiados intentos. Intenta de nuevo en unos minutos.'}, status=429)

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, TypeError):
            data = request.POST.dict()

        email = (data.get('email') or '').strip().lower()
        redirect_url = data.get('redirect_url', '/')
        is_onboarding = data.get('is_onboarding', False)
        onboarding_data = data.get('onboarding_data', {})

        if not email:
            return JsonResponse({'error': 'Email es obligatorio'}, status=400)

        if isinstance(onboarding_data, str):
            try:
                onboarding_data = json.loads(onboarding_data)
            except json.JSONDecodeError:
                onboarding_data = {}

        from core.models.magic_link import MagicLinkToken
        from django.utils import timezone
        from datetime import timedelta

        MagicLinkToken.objects.filter(email=email, used_at__isnull=True).update(used_at=timezone.now())

        token_obj = MagicLinkToken.objects.create(
            email=email,
            token=MagicLinkToken.generate_token(),
            expires_at=timezone.now() + timedelta(minutes=15),
            redirect_url=redirect_url,
            is_onboarding=is_onboarding,
            onboarding_data=onboarding_data,
        )

        from core.services.magic_link_service import send_magic_link_email
        try:
            send_magic_link_email(token_obj, request=request)
        except Exception as e:
            logger.error('Failed to send magic link email to %s: %s', email, e)
            return JsonResponse({'error': 'Error enviando el email. Intenta de nuevo.'}, status=500)

        return JsonResponse({
            'message': 'Enlace mágico enviado a tu email',
            'email': email,
            'expires_in_minutes': 15,
        })


class MagicLinkVerifyView(View):
    def get(self, request, token):
        from core.services.magic_link_service import verify_magic_link

        token_obj, status = verify_magic_link(token)

        if status in ('invalid', 'expired', 'already_used'):
            error_map = {
                'invalid': 'Este enlace no existe o fue reemplazado.',
                'expired': 'Este enlace ya expiró. Solicita uno nuevo.',
                'already_used': 'Este enlace ya fue utilizado.',
            }
            return render(request, 'auth/magic_link_error.html', {
                'error': error_map.get(status, 'Error'),
                'can_retry': status in ('expired', 'already_used'),
                'email': token_obj.email if token_obj else '',
            }, status=400)

        user, created = User.objects.get_or_create(
            email=token_obj.email,
            defaults={
                'username': token_obj.email,
                'is_active': True,
            },
        )

        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        if token_obj.is_onboarding and token_obj.onboarding_data:
            request.session['onboarding_data'] = token_obj.onboarding_data
            request.session['onboarding_email'] = token_obj.email
            return redirect('/onboarding/agency/')

        redirect_url = token_obj.redirect_url or '/'
        return redirect(redirect_url)


class SaaSOnboardingView(View):
    template_name = "onboarding/b2b_onboarding.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        import stripe

        admin_email = request.POST.get('admin_email')
        agency_name = request.POST.get('agency_name')
        subdomain = request.POST.get('subdomain')
        plan = request.POST.get('plan', 'BASIC')
        brand_color = request.POST.get('brand_color', '#3b82f6')

        if User.objects.filter(email=admin_email).exists():
            return render(request, self.template_name, {'error': "El email ya esta registrado."})

        if Agencia.objects.filter(subdominio_slug=subdomain).exists():
            return render(request, self.template_name, {'error': "El subdominio ya esta en uso."})

        plan_data = PLAN_CONFIG.get(plan, PLAN_CONFIG['BASIC'])
        price_id = plan_data.get('stripe_price_id')

        if not price_id and plan != 'FREE':
            return JsonResponse({'error': 'Configuracion de precios no disponible'}, status=500)

        try:
            metadata = {
                'admin_email': admin_email,
                'agency_name': agency_name,
                'subdomain': subdomain,
                'brand_color': brand_color,
                'plan': plan,
                'onboarding': 'true',
                'auth_method': 'magic_link',
            }

            if plan == 'FREE':
                self._provision_agency(admin_email, agency_name, subdomain, plan, brand_color)
                return redirect(reverse('billing_success'))

            stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }] if price_id else [{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {'name': f'TravelHub ERP - Plan {plan} (Trial)'},
                        'unit_amount': 0,
                        'recurring': {'interval': 'month'},
                    },
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=request.build_absolute_uri(reverse('billing_success')) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=request.build_absolute_uri(reverse('billing_cancel')),
                customer_email=admin_email,
                metadata=metadata,
            )
            return redirect(checkout_session.url, code=303)

        except Exception as e:
            logger.error('Error SaaSOnboardingView Stripe: %s', e)
            return render(request, self.template_name, {'error': f'Error al iniciar el pago: {e}'})

    def _provision_agency(self, email, agency_name, subdomain, plan, brand_color):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={'username': email, 'is_active': True},
        )
        agencia = Agencia.objects.create(
            nombre=agency_name,
            subdominio_slug=subdomain,
            plan=plan,
            color_primario=brand_color,
        )
        UsuarioAgencia.objects.create(
            usuario=user,
            agencia=agencia,
            rol='admin',
        )
        return user, agencia


class OnboardingAgencyView(View):
    template_name = "onboarding/step2_agency.html"

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('/onboarding/')

        onboarding_data = request.session.get('onboarding_data', {})
        return render(request, self.template_name, {
            'email': request.user.email,
            'onboarding_data': onboarding_data,
            'plans': PLAN_CONFIG,
        })

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('/onboarding/')

        agency_name = request.POST.get('agency_name', '').strip()
        subdomain = request.POST.get('subdomain', '').strip().lower()
        plan = request.POST.get('plan', 'FREE')
        brand_color = request.POST.get('brand_color', '#3b82f6')
        country = request.POST.get('country', 'VE')
        currency = request.POST.get('currency', 'USD')

        if not agency_name or not subdomain:
            return render(request, self.template_name, {
                'error': 'Nombre de agencia y subdominio son obligatorios.',
                'plans': PLAN_CONFIG,
            })

        if Agencia.objects.filter(subdominio_slug=subdomain).exists():
            return render(request, self.template_name, {
                'error': 'El subdominio ya esta en uso.',
                'plans': PLAN_CONFIG,
            })

        agencia = Agencia.objects.create(
            nombre=agency_name,
            subdominio_slug=subdomain,
            plan=plan,
            color_primario=brand_color,
        )

        UsuarioAgencia.objects.create(
            usuario=request.user,
            agencia=agencia,
            rol='admin',
        )

        agencia.actualizar_limites_por_plan()

        if plan == 'FREE':
            return redirect('/dashboard/')

        import stripe
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
        plan_data = PLAN_CONFIG.get(plan, PLAN_CONFIG['BASIC'])
        price_id = plan_data.get('stripe_price_id')

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{'price': price_id, 'quantity': 1}],
                mode='subscription',
                success_url=request.build_absolute_uri(reverse('billing_success')) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=request.build_absolute_uri(reverse('billing_cancel')),
                customer_email=request.user.email,
                metadata={
                    'admin_email': request.user.email,
                    'agency_name': agency_name,
                    'subdomain': subdomain,
                    'plan': plan,
                    'onboarding': 'true',
                },
            )
            return redirect(checkout_session.url, code=303)
        except Exception as e:
            logger.error('Stripe checkout error during onboarding: %s', e)
            return redirect('/dashboard/')
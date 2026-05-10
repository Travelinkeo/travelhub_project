import json
import logging
from django.conf import settings
from django.contrib.auth import login, get_user_model
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.models.magic_link import MagicLinkToken
from core.services.magic_link_service import create_magic_link, send_magic_link_email, verify_magic_link

logger = logging.getLogger(__name__)
User = get_user_model()


@method_decorator(csrf_exempt, name='dispatch')
class MagicLinkRequestView(View):
    def post(self, request):
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

        MagicLinkToken.objects.filter(email=email, used_at__isnull=True).update(used_at=timezone.now())

        token_obj = create_magic_link(
            email=email,
            redirect_url=redirect_url,
            is_onboarding=is_onboarding,
            onboarding_data=onboarding_data,
        )

        try:
            send_magic_link_email(token_obj, request=request)
        except Exception as e:
            logger.error('Failed to send magic link email to %s: %s', email, e)
            return JsonResponse({'error': 'Error enviando el email. Intenta de nuevo.'}, status=500)

        return JsonResponse({
            'message': 'Enlace magic enviado a tu email',
            'email': email,
            'expires_in_minutes': 15,
        })


class MagicLinkVerifyView(View):
    def get(self, request, token):
        token_obj, status = verify_magic_link(token)

        if status == 'invalid':
            return render(request, 'auth/magic_link_error.html', {
                'error': 'Enlace inválido',
                'error_detail': 'Este enlace no existe o fue reemplazado por uno más reciente.',
            }, status=400)

        if status == 'expired':
            return render(request, 'auth/magic_link_error.html', {
                'error': 'Enlace expirado',
                'error_detail': 'Este enlace ya expiró. Solicita uno nuevo.',
                'can_retry': True,
                'email': token_obj.email if token_obj else '',
            }, status=400)

        if status == 'already_used':
            return render(request, 'auth/magic_link_error.html', {
                'error': 'Enlace ya utilizado',
                'error_detail': 'Este enlace ya fue utilizado. Solicita uno nuevo.',
                'can_retry': True,
            }, status=400)

        if not token_obj:
            return render(request, 'auth/magic_link_error.html', {
                'error': 'Error desconocido',
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
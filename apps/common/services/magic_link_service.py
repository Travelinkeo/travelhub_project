import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from core.models.magic_link import MagicLinkToken

logger = logging.getLogger(__name__)

MAGIC_LINK_EXPIRY_MINUTES = 15


def create_magic_link(email, redirect_url='', is_onboarding=False, onboarding_data=None):
    token_obj = MagicLinkToken.objects.create(
        email=email.lower().strip(),
        token=MagicLinkToken.generate_token(),
        expires_at=timezone.now() + timedelta(minutes=MAGIC_LINK_EXPIRY_MINUTES),
        redirect_url=redirect_url,
        is_onboarding=is_onboarding,
        onboarding_data=onboarding_data or {},
    )
    return token_obj


def send_magic_link_email(token_obj, request=None):
    base_url = getattr(settings, 'MAGIC_LINK_BASE_URL', '')
    if not base_url and request:
        scheme = 'https' if request.is_secure() else 'http'
        base_url = f'{scheme}://{request.get_host()}'

    magic_url = f'{base_url}/auth/magic/{token_obj.token}/'

    if token_obj.is_onboarding and token_obj.redirect_url:
        magic_url = f'{magic_url}?next={token_obj.redirect_url}'

    context = {
        'magic_url': magic_url,
        'email': token_obj.email,
        'expiry_minutes': MAGIC_LINK_EXPIRY_MINUTES,
        'is_onboarding': token_obj.is_onboarding,
        'site_name': getattr(settings, 'SITE_NAME', 'TravelHub'),
    }

    subject = 'Confirma tu acceso a TravelHub' if token_obj.is_onboarding else 'Tu enlace de acceso a TravelHub'

    try:
        html_body = render_to_string('auth/magic_link_email.html', context)
        text_body = render_to_string('auth/magic_link_email.txt', context)
    except Exception:
        html_body = f'<p>Haz clic en el siguiente enlace para acceder a TravelHub:</p><p><a href="{magic_url}">{magic_url}</a></p><p>Este enlace expira en {MAGIC_LINK_EXPIRY_MINUTES} minutos.</p>'
        text_body = f'Accede a TravelHub copiando este enlace en tu navegador:\n{magic_url}\n\nEste enlace expira en {MAGIC_LINK_EXPIRY_MINUTES} minutos.'

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@travelhub.cc')

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[token_obj.email],
    )
    msg.attach_alternative(html_body, 'text/html')
    msg.send()

    logger.info('Magic link email sent to %s', token_obj.email)
    return True


def verify_magic_link(token_str):
    try:
        token_obj = MagicLinkToken.objects.get(token=token_str)
    except MagicLinkToken.DoesNotExist:
        logger.warning('Magic link token not found: %s...', token_str[:8])
        return None, 'invalid'

    if not token_obj.is_valid:
        if token_obj.used_at is not None:
            return None, 'already_used'
        return None, 'expired'

    token_obj.mark_used()
    return token_obj, 'valid'
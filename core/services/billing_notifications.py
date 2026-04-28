"""Servicio de notificaciones de billing por email."""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from datetime import date, timedelta


def enviar_email_trial_expirando(agencia, dias_restantes):
    """Envía email cuando el trial está por expirar."""
    subject = f'Tu trial de TravelHub expira en {dias_restantes} días'
    
    context = {
        'agencia': agencia,
        'dias_restantes': dias_restantes,
        'upgrade_url': f'{settings.FRONTEND_URL}/billing/plans',
    }
    
    html_message = render_to_string('emails/trial_expirando.html', context)
    
    send_mail(
        subject=subject,
        message=f'Tu trial expira en {dias_restantes} días. Actualiza tu plan para continuar.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[agencia.email_principal],
        html_message=html_message,
        fail_silently=True,
    )


def enviar_email_trial_expirado(agencia):
    """Envía email cuando el trial ha expirado."""
    subject = 'Tu trial de TravelHub ha expirado'
    
    context = {
        'agencia': agencia,
        'upgrade_url': f'{settings.FRONTEND_URL}/billing/plans',
    }
    
    html_message = render_to_string('emails/trial_expirado.html', context)
    
    send_mail(
        subject=subject,
        message='Tu trial ha expirado. Actualiza tu plan para continuar usando TravelHub.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[agencia.email_principal],
        html_message=html_message,
        fail_silently=True,
    )


def enviar_email_pago_exitoso(agencia, invoice_data):
    """Envía email de confirmación de pago."""
    subject = f'Pago recibido - TravelHub {agencia.get_plan_display()}'
    
    context = {
        'agencia': agencia,
        'invoice': invoice_data,
    }
    
    html_message = render_to_string('emails/pago_exitoso.html', context)
    
    send_mail(
        subject=subject,
        message=f'Hemos recibido tu pago de ${invoice_data["amount"]}. Gracias por usar TravelHub.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[agencia.email_principal],
        html_message=html_message,
        fail_silently=True,
    )


def enviar_email_pago_fallido(agencia):
    """Envía email cuando falla un pago."""
    subject = 'Problema con tu pago - TravelHub'
    
    context = {
        'agencia': agencia,
        'billing_url': f'{settings.FRONTEND_URL}/billing',
    }
    
    html_message = render_to_string('emails/pago_fallido.html', context)
    
    send_mail(
        subject=subject,
        message='Hubo un problema procesando tu pago. Por favor actualiza tu método de pago.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[agencia.email_principal],
        html_message=html_message,
        fail_silently=True,
    )


def enviar_email_bienvenida(agencia):
    """Envía email de bienvenida al suscribirse."""
    subject = f'¡Bienvenido a TravelHub {agencia.get_plan_display()}!'
    
    context = {
        'agencia': agencia,
        'dashboard_url': f'{settings.FRONTEND_URL}/dashboard',
    }
    
    html_message = render_to_string('emails/bienvenida.html', context)
    
    send_mail(
        subject=subject,
        message=f'¡Bienvenido a TravelHub! Tu plan {agencia.get_plan_display()} está activo.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[agencia.email_principal],
        html_message=html_message,
        fail_silently=True,
    )


def enviar_email_limite_alcanzado(agencia, tipo_limite):
    """Envía email cuando se alcanza un límite."""
    subject = f'Límite de {tipo_limite} alcanzado - TravelHub'
    
    context = {
        'agencia': agencia,
        'tipo_limite': tipo_limite,
        'upgrade_url': f'{settings.FRONTEND_URL}/billing/plans',
    }
    
    html_message = render_to_string('emails/limite_alcanzado.html', context)
    
    send_mail(
        subject=subject,
        message=f'Has alcanzado el límite de {tipo_limite} de tu plan. Considera actualizar.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[agencia.email_principal],
        html_message=html_message,
        fail_silently=True,
    )

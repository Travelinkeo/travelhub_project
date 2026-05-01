import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)

class NotificationService:
    """
    SERVICIO CENTRAL DE NOTIFICACIONES:
    Gestiona el envío de correos electrónicos profesionales, 
    notificaciones push y mensajes de WhatsApp.
    """

    @staticmethod
    def enviar_reporte_pdf_email(agencia, email_destino, pdf_bytes, kpis):
        """
        Envía el reporte de conciliación consolidado por correo electrónico 
        con el PDF adjunto directamente desde memoria.
        """
        subject = f"📊 Reporte de Conciliación Consolidado - {agencia.nombre}"
        
        # 1. Preparar el contexto para el template de correo
        context = {
            'agencia_nombre': agencia.nombre,
            'kpis': kpis,
            'color_primario': agencia.color_primario or "#10b981",
        }

        # 2. Renderizar el HTML y generar la versión en texto plano
        html_content = render_to_string('finance/emails/reconciliation_summary.html', context)
        text_content = strip_tags(html_content)

        # 3. Construir el objeto de correo
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email_destino]
        )
        email.attach_alternative(html_content, "text/html")

        # 4. ADJUNTAR EL PDF DESDE MEMORIA (Crucial para Performance)
        filename = f"Reporte_Gestion_{agencia.nombre.replace(' ', '_')}.pdf"
        email.attach(filename, pdf_bytes.getvalue(), 'application/pdf')

        try:
            email.send()
            logger.info(f"✅ Email de reporte enviado exitosamente a {email_destino} para {agencia.nombre}")
            return True
        except Exception as e:
            logger.error(f"❌ Error enviando email de reporte a {email_destino}: {str(e)}")
            raise e

    @staticmethod
    def enviar_bienvenida_agencia(agencia, user):
        """
        Envía el correo de bienvenida a una nueva agencia.
        """
        subject = f"🚀 ¡Bienvenido a TravelHub! - {agencia.nombre} está lista"
        
        context = {
            'agencia_nombre': agencia.nombre,
            'admin_name': user.first_name or user.username,
            'admin_email': user.email,
            'subdominio': agencia.subdominio_slug,
            'color_primario': agencia.color_primario or "#3b82f6",
        }

        html_content = render_to_string('onboarding/welcome_email.html', context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email.attach_alternative(html_content, "text/html")

        try:
            email.send()
            logger.info(f"🚀 Email de bienvenida enviado a {user.email}")
            return True
        except Exception as e:
            logger.error(f"❌ Error enviando email de bienvenida: {str(e)}")
            return False

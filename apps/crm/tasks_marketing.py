import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from apps.crm.models import Cliente

logger = logging.getLogger(__name__)

@shared_task(queue='notifications', max_retries=2)
def despachar_campana_masiva_task(cliente_ids: list, asunto: str, cuerpo_html_template: str):
    """
    Toma una lista de IDs, inyecta el nombre real del cliente en el template de la IA,
    y envía los correos masivamente usando el canal de notificaciones.
    """
    clientes = Cliente.objects.filter(id__in=cliente_ids)
    enviados = 0
    fallidos = 0

    for cliente in clientes:
        if not cliente.email:
            continue
            
        try:
            # Reemplazar la variable mágica de la IA con el nombre real
            nombre_mostrar = cliente.nombres.split()[0].title() if cliente.nombres else "Viajero"
            cuerpo_personalizado = cuerpo_html_template.replace("{{ nombre_cliente }}", nombre_mostrar)
            
            send_mail(
                subject=asunto,
                message="Tu cliente de correo no soporta HTML. Por favor contáctanos.",
                html_message=cuerpo_personalizado,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[cliente.email],
                fail_silently=False,
            )
            enviados += 1
            
        except Exception as e:
            logger.error(f"Fallo enviando campaña a {cliente.email}: {e}")
            fallidos += 1
            
    logger.info(f"🚀 Campaña Finalizada: {enviados} enviados, {fallidos} fallidos.")
    return f"Campaña '{asunto[:20]}...': {enviados} envíos exitosos."

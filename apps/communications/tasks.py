import logging

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name="apps.communications.tasks.send_lead_followup_email",
    queue="default",
    time_limit=120,
)
def send_lead_followup_email():
    """
    Envía emails de seguimiento a leads capturados que no se han convertido.
    - Primera semana: email a las 24h con caso de éxito
    - Segunda semana: email a las 72h con demo personalizada
    """
    from apps.communications.models import Lead
    from apps.communications.services.email_unified import send_custom_email

    now = timezone.now()
    sent_count = 0

    leads = Lead.objects.filter(email_enviado=True)

    for lead in leads:
        if not lead.email:
            continue

        lock_key_1 = f"lead_followup_1:{lead.id}"
        lock_key_2 = f"lead_followup_2:{lead.id}"

        hours_since = (now - lead.created_at).total_seconds() / 3600

        if 23 <= hours_since <= 25 and not lead._followup_1_sent:
            if cache.get(lock_key_1):
                continue
            cache.set(lock_key_1, True, 3600)

            sent = send_custom_email(
                subject="Cómo una agencia en Caracas triplicó sus ventas con TravelHub",
                recipient=lead.email,
                template_name="emails/lead_followup_1.html",
                context={
                    "nombre": lead.nombre or "Agente",
                },
            )
            if sent:
                lead._followup_1_sent = True
                lead.save(update_fields=["_followup_1_sent"])
                sent_count += 1
                logger.info(f"Follow-up 1 enviado a {lead.email}")

        elif 71 <= hours_since <= 73 and not lead._followup_2_sent:
            if cache.get(lock_key_2):
                continue
            cache.set(lock_key_2, True, 3600)

            sent = send_custom_email(
                subject="🎯 Demo personalizada: TravelHub en 5 minutos",
                recipient=lead.email,
                template_name="emails/lead_followup_2.html",
                context={
                    "nombre": lead.nombre or "Agente",
                },
            )
            if sent:
                lead._followup_2_sent = True
                lead.save(update_fields=["_followup_2_sent"])
                sent_count += 1
                logger.info(f"Follow-up 2 enviado a {lead.email}")

    if sent_count:
        logger.info(f"Lead follow-ups enviados: {sent_count}")
    return sent_count

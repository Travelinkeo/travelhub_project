import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from core.signals_bypass import are_signals_blocked

logger = logging.getLogger(__name__)


@receiver(post_save, sender="crm.PasaporteEscaneado")
def process_passport_on_save(sender, instance, created, **kwargs):
    """Función: process passport on save."""
    if are_signals_blocked():
        return

    if created and instance.imagen_original and not instance.numero_pasaporte:
        from apps.crm.tasks import process_passport_ocr

        process_passport_ocr.delay(instance.pk)
        logger.info(f"Passport OCR despachado a Celery para PasaporteEscaneado {instance.pk}")

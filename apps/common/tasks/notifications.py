import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,
    time_limit=60,
    soft_time_limit=50,
)
def enviar_bienvenida_agencia_task(self, agencia_id, user_id):
    from django.contrib.auth import get_user_model

    from apps.communications.services.notification_dispatcher import NotificationService
    from core.models.agencia import Agencia

    User = get_user_model()
    try:
        agencia = Agencia.objects.get(pk=agencia_id)
        user = User.objects.get(pk=user_id)
        NotificationService.enviar_bienvenida_agencia(agencia, user)
        logger.info(f"Welcome email sent to {user.email} for agencia {agencia.nombre}")
        return True
    except Exception as exc:
        logger.error(f"Welcome email task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=10,
    time_limit=120,
    soft_time_limit=100,
)
def notificar_confirmacion_pago_task(self, pago_id):
    from apps.bookings.models import PagoVenta
    from apps.communications.services.notification_dispatcher import notificar_confirmacion_pago

    try:
        pago = PagoVenta.objects.get(pk=pago_id)
        notificar_confirmacion_pago(pago)
        logger.info(f"Payment notification sent for pago {pago_id}")
        return True
    except Exception as exc:
        logger.error(f"Payment notification task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=10,
    time_limit=120,
    soft_time_limit=100,
)
def notificar_recordatorio_pago_task(self, venta_id):
    from apps.bookings.models import Venta
    from apps.communications.services.notification_dispatcher import notificar_recordatorio_pago

    try:
        venta = Venta.objects.get(pk=venta_id)
        notificar_recordatorio_pago(venta)
        logger.info(f"Payment reminder sent for venta {venta_id}")
        return True
    except Exception as exc:
        logger.error(f"Payment reminder task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=10,
    time_limit=120,
    soft_time_limit=100,
)
def notificar_boleto_procesado_task(self, boleto_id):
    from apps.bookings.models import BoletoImportado
    from apps.communications.services.notification_dispatcher import notificar_boleto_procesado

    try:
        boleto = BoletoImportado.objects.get(pk=boleto_id)
        notificar_boleto_procesado(boleto)
        logger.info(f"Ticket processed notification sent for boleto {boleto_id}")
        return True
    except Exception as exc:
        logger.error(f"Ticket processed notification task error: {exc}")
        self.retry(exc=exc)

import logging
import datetime
from django.db import models
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.conf import settings

from .models import BoletoImportado, PagoVenta, Venta, CircuitoDia

logger = logging.getLogger(__name__)

@receiver(post_save, sender=BoletoImportado)
def signal_boleto_post_save(sender, instance, created, **kwargs):
    """
    DISPARADOR DE TAX REFUND:
    Al terminar el procesamiento exitoso del boleto, encolamos el análisis 
    de recupero de impuestos.
    """
    if instance.estado_parseo == 'COM': 
        # 1. Disparar Tax Refund
        try:
             from apps.finance.tasks_tax_refund import evaluar_tax_refund_task
             evaluar_tax_refund_task.delay(instance.pk)
        except (ImportError, Exception) as e:
             logger.error(f"Error disparando Tax Refund: {e}")

        # 2. WORKFLOW MÁGICO: Automatización de Venta
        # NOTA: La creación de venta ahora es orquestada EXCLUSIVAMENTE por TicketParserService
        pass

@receiver(post_save, sender=PagoVenta)
def signal_pago_post_save(sender, instance, created, **kwargs):  # pragma: no cover
    if instance.venta:
        instance.venta.recalcular_finanzas()
        
        # Contabilidad registrada en apps/contabilidad/signals.py

        if instance.venta.pk:
             instance.venta._evaluar_otorgar_puntos(contexto="signal_pago_post_save")

@receiver(post_delete, sender=PagoVenta)
def signal_pago_post_delete(sender, instance, **kwargs):  # pragma: no cover
    try:
        if instance.venta:
            instance.venta.recalcular_finanzas()
            if instance.venta.pk:
                instance.venta._evaluar_otorgar_puntos(contexto="signal_pago_post_save")
    except Exception:
        pass

@receiver(pre_save, sender=Venta)
def capturar_estado_anterior_venta(sender, instance, **kwargs):
    """
    Captura el estado actual en DB antes de guardar los cambios 
    para poder detectar transiciones de estado en el post_save.
    """
    if instance.pk:
        try:
            obj_db = Venta.all_objects.get(pk=instance.pk)
            instance._estado_anterior = obj_db.estado
        except Venta.DoesNotExist:
            instance._estado_anterior = None
    else:
        instance._estado_anterior = None


@receiver(post_save, sender=Venta)
def venta_post_save_dispatcher(sender, instance, created, **kwargs):
    """
    Dispatcher centralizado para todos los post_save de Venta.
    Evita múltiples handlers dispersos y garantiza orden de ejecución.
    """
    if kwargs.get('raw', False):
        return

    estado_anterior = getattr(instance, '_estado_anterior', None)
    estado_actual = instance.estado

    # 1. Email de confirmación (solo en creación)
    if created and instance.cliente and instance.cliente.email:
        try:
            from core.services.email_service import enviar_confirmacion_venta
            enviar_confirmacion_venta(instance)
        except Exception as e:
            logger.exception(f"Error enviando email confirmación para venta {instance.id_venta}: {e}")

    # 2. Email de cambio de estado (solo en actualización con cambio de estado)
    if not created and estado_anterior and estado_anterior != estado_actual:
        try:
            if instance.cliente and instance.cliente.email:
                from core.services.email_service import enviar_cambio_estado
                enviar_cambio_estado(instance, estado_anterior)
        except Exception as e:
            logger.warning(f"Omitiendo email cambio estado para Venta {instance.pk}: {e}")

    # 3. Notificación WhatsApp al pagar (transición a PAGADA_TOTAL)
    recien_pagada = (estado_actual == Venta.EstadoVenta.PAGADA_TOTAL) and (estado_anterior != Venta.EstadoVenta.PAGADA_TOTAL)
    if recien_pagada:
        try:
            from .tasks import notificar_pago_whatsapp_task
            notificar_pago_whatsapp_task.delay(instance.pk)
            logger.info(f"[SIGNAL] Tarea WhatsApp encolada para Venta {instance.pk}")
        except Exception as e:
            logger.error(f"[SIGNAL] Error disparando WhatsApp: {e}")

    # 4. Notificaciones in-app/push
    try:
        from core.notification_service import notificar_confirmacion_venta, notificar_cambio_estado
        if created:
            notificar_confirmacion_venta(instance)
        elif estado_anterior and estado_anterior != estado_actual:
            notificar_cambio_estado(instance, estado_anterior)
    except Exception as e:
        logger.debug(f"Notificación in-app omitida para Venta {instance.pk}: {e}")

@receiver([post_save, post_delete], sender=CircuitoDia)
def actualizar_circuito_dias(sender, instance, **kwargs):  # pragma: no cover
    """Actualiza la cantidad de días y la fecha de fin del circuito asociado."""
    circuito = instance.circuito
    if not circuito:
        return
        
    max_dia = circuito.dias.aggregate(models.Max('dia_numero'))['dia_numero__max'] or 0
    if max_dia:
        circuito.dias_total = max_dia
        if circuito.fecha_inicio:
            circuito.fecha_fin = circuito.fecha_inicio + datetime.timedelta(days=max_dia - 1)
    else:
        circuito.dias_total = None
        circuito.fecha_fin = None
    circuito.save(update_fields=['dias_total', 'fecha_fin'])

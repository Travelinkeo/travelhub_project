import datetime
import logging

from django.db import models, transaction

from apps.bookings.models.venta import Venta
from core.api import sale_recalculation_requested

logger = logging.getLogger(__name__)


class VentaService:
    """
    Service layer to explicitly orchestrate operations on Venta and its related models
    (ItemVenta, PagoVenta, FeeVenta, CircuitoDia), completely decoupled from implicit signals.
    """

    @staticmethod
    def recalculate_finances(venta_id):
        """
        Dispatches a 'sale_recalculation_requested' event.
        """
        try:
            # Para obtener el agencia_id, necesitamos la instancia de la venta.
            # Este es un trade-off aceptable para lograr el desacoplamiento.
            venta = Venta.objects.get(pk=venta_id)

            # Emitimos la señal. 'finance' u otros módulos escucharán este evento.
            sale_recalculation_requested.send(
                sender=Venta, venta_id=venta.pk, agencia_id=venta.agencia_id
            )
            logger.info(
                f"📢 VentaService: Evento 'sale_recalculation_requested' emitido para Venta {venta_id}"
            )
            return True
        except Venta.DoesNotExist:
            logger.error(
                f"Error en VentaService.recalculate_finances: Venta con id={venta_id} no encontrada."
            )
            return False
        except Exception as e:
            logger.error(f"Error en VentaService.recalculate_finances al emitir evento: {e}")
            return False

    @staticmethod
    def evaluate_loyalty_points(pago_venta):
        """
        Evaluates and awards loyalty points for confirmed payments on a sale.
        """
        if pago_venta.venta and pago_venta.venta.pk:
            try:
                pago_venta.venta._evaluar_otorgar_puntos(
                    contexto="VentaService.evaluate_loyalty_points"
                )
                logger.info(
                    f"🎖️ VentaService: Evaluated loyalty points for Venta {pago_venta.venta.pk}"
                )
                return True
            except Exception as e:
                logger.error(f"Error in VentaService.evaluate_loyalty_points: {e}")
        return False

    @staticmethod
    def dispatch_post_save_actions(venta, created, estado_anterior=None):
        """
        Centralized orchestrator for all post-save actions on a Venta instance.
        """
        estado_actual = venta.estado

        # 1. SaaS Quota Increment
        if created and venta.agencia_id:
            try:
                from apps.common.services.saas_quota_service import SaaSQuotaService

                SaaSQuotaService.increment_usage(venta.agencia_id, "sales_per_month")
            except Exception as e:
                logger.warning(
                    f"Error VentaService: SaaS quota increment failed for Venta {venta.id_venta}: {e}"
                )

        # 2. Confirmation Emails + WhatsApp
        if created and venta.cliente and venta.cliente.email:
            try:
                from apps.communications.services.email_unified import enviar_confirmacion_venta

                transaction.on_commit(lambda: enviar_confirmacion_venta(venta))
            except Exception as e:
                logger.exception(
                    f"Error VentaService: Confirmation email failed for Venta {venta.id_venta}: {e}"
                )

        if created and venta.cliente and venta.cliente.telefono_principal:
            try:
                from apps.communications.services.whatsapp_unified import (
                    enviar_whatsapp_confirmacion_venta,
                )

                transaction.on_commit(
                    lambda: enviar_whatsapp_confirmacion_venta(venta)
                )
            except Exception as e:
                logger.warning(
                    f"Error VentaService: WhatsApp confirmation failed for Venta {venta.id_venta}: {e}"
                )

        # 3. State Change Emails + WhatsApp
        if not created and estado_anterior and estado_anterior != estado_actual:
            if venta.cliente and venta.cliente.email:
                try:
                    from apps.communications.services.email_unified import enviar_cambio_estado

                    transaction.on_commit(lambda: enviar_cambio_estado(venta, estado_anterior))
                except Exception as e:
                    logger.warning(
                        f"Error VentaService: State change email failed for Venta {venta.pk}: {e}"
                    )

            if venta.cliente and venta.cliente.telefono_principal:
                try:
                    from apps.communications.services.whatsapp_unified import (
                        enviar_whatsapp_cambio_estado,
                    )

                    transaction.on_commit(
                        lambda: enviar_whatsapp_cambio_estado(venta, estado_anterior)
                    )
                except Exception as e:
                    logger.warning(
                        f"Error VentaService: WhatsApp state change failed for Venta {venta.pk}: {e}"
                    )

        # 4. WhatsApp Notification
        recien_pagada = (estado_actual == Venta.EstadoVenta.PAGADA_TOTAL) and (
            estado_anterior != Venta.EstadoVenta.PAGADA_TOTAL
        )
        if recien_pagada:
            try:
                from django.db import transaction

                from apps.bookings.tasks import notificar_pago_whatsapp_task

                transaction.on_commit(
                    lambda: notificar_pago_whatsapp_task.delay(
                        venta.pk, agencia_id=venta.agencia_id
                    )
                )
                logger.info(
                    f"📲 VentaService: WhatsApp notification task queued for Venta {venta.pk}"
                )
            except Exception as e:
                logger.error(f"Error VentaService: WhatsApp dispatcher failed: {e}")

        # 5. In-App Notifications
        try:
            from apps.communications.services.notification_service import (
                notificar_cambio_estado,
                notificar_confirmacion_venta,
            )

            if created:
                notificar_confirmacion_venta(venta)
            elif estado_anterior and estado_anterior != estado_actual:
                notificar_cambio_estado(venta, estado_anterior)
        except Exception as e:
            logger.debug(f"VentaService: In-app notification omitted for Venta {venta.pk}: {e}")

    @staticmethod
    def update_circuit_days(circuito_dia):
        """
        Updates the duration and end date of the Circuit associated with CircuitoDia.
        """
        circuito = circuito_dia.circuito
        if not circuito:
            return False

        try:
            max_dia = circuito.dias.aggregate(models.Max("dia_numero"))["dia_numero__max"] or 0
            if max_dia:
                circuito.dias_total = max_dia
                if circuito.fecha_inicio:
                    circuito.fecha_fin = circuito.fecha_inicio + datetime.timedelta(
                        days=max_dia - 1
                    )
            else:
                circuito.dias_total = None
                circuito.fecha_fin = None
            circuito.save(update_fields=["dias_total", "fecha_fin"])
            logger.info(f"🔄 VentaService: Updated circuit days for Circuit {circuito.pk}")
            return True
        except Exception as e:
            logger.error(f"Error in VentaService.update_circuit_days: {e}")
        return False

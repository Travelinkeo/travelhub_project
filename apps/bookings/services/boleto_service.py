import logging
from django.db import transaction

logger = logging.getLogger(__name__)

class BoletoImportadoService:
    """
    Service layer to explicitly orchestrate operations on BoletoImportado,
    completely decoupled from implicit signals.
    """

    @staticmethod
    def trigger_parsing_if_needed(boleto_importado):
        """
        Triggers parsing asynchronously via Celery if the boleto has a file
        but has not been parsed yet.
        """
        from apps.bookings.models import BoletoImportado
        
        # Permitir bypass explícito
        if getattr(boleto_importado, '_skip_auto_parse', False):
            logger.info(f"⏭️ BoletoImportadoService: Bypass activado para Boleto {boleto_importado.pk}.")
            return False

        if boleto_importado.archivo_boleto and not boleto_importado.datos_parseados:
            try:
                # ATOMIC LOCK: Try to update status from PENDIENTE to EN_PROCESO.
                updated_count = BoletoImportado.objects.filter(
                    pk=boleto_importado.pk, 
                    estado_parseo=BoletoImportado.EstadoParseo.PENDIENTE
                ).update(estado_parseo=BoletoImportado.EstadoParseo.EN_PROCESO)

                if updated_count > 0:
                    from core.tasks import parsear_boleto_individual
                    logger.info(f"🧩 BoletoImportadoService: Lock adquirido para Boleto {boleto_importado.pk}. Disparando Celery...")
                    from django.db import transaction
                    transaction.on_commit(lambda: parsear_boleto_individual.delay(boleto_importado.pk))
                    return True
                else:
                    logger.info(f"🧩 BoletoImportadoService: Boleto {boleto_importado.pk} ya no está PENDIENTE o Lock falló.")
            except Exception as e:
                logger.error(f"Error in BoletoImportadoService.trigger_parsing_if_needed: {e}")
        return False

    @staticmethod
    def post_parse_automation(boleto_importado):
        """
        Orchestrates sales creation, automatic invoicing, and notifications after a boleto is parsed.
        """
        if not boleto_importado.datos_parseados or boleto_importado.venta_asociada:
            return None

        with transaction.atomic():
            try:
                from apps.bookings.services.automation import VentaAutomationService
                venta = VentaAutomationService.process_ticket_import(boleto_importado)
                
                if not venta:
                    return None

                # --- Auto-Invoicing ---
                if boleto_importado.formato_detectado and boleto_importado.formato_detectado.startswith('EML'):
                    try:
                        from apps.finance.services.invoice_service import InvoiceService
                        InvoiceService.create_invoice_from_sale(venta.id_venta)
                    except Exception as e_fact:
                        logger.error(f"⚠️ BoletoImportadoService: Error en factura automática: {e_fact}")

                # --- Notifications ---
                if boleto_importado.archivo_pdf_generado and not boleto_importado.telegram_file_id:
                    try:
                        from apps.communications.services.notification_dispatcher import notificar_boleto_procesado
                        notificar_boleto_procesado(boleto_importado)
                    except Exception as e_notif:
                        logger.error(f"⚠️ BoletoImportadoService: Error en notificación: {e_notif}")

                return venta
            except Exception as e:
                logger.error(f"❌ BoletoImportadoService: Error crítico en post_parse_automation para Boleto {boleto_importado.pk}: {e}")
                return None

    @staticmethod
    def evaluate_tax_refund(boleto_importado):
        """
        Triggers tax refund evaluation when a ticket is successfully parsed and marked as complete.
        """
        if boleto_importado.estado_parseo == 'COM':
            try:
                from apps.finance.tasks_tax_refund import evaluar_tax_refund_task
                from django.db import transaction
                transaction.on_commit(lambda: evaluar_tax_refund_task.delay(boleto_importado.pk))
                logger.info(f"💰 BoletoImportadoService: Tax Refund task queued for Boleto {boleto_importado.pk}")
                return True
            except (ImportError, Exception) as e:
                logger.error(f"Error in BoletoImportadoService.evaluate_tax_refund: {e}")
        return False

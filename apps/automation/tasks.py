import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, queue="ia_fast", soft_time_limit=20, time_limit=30)
def process_web_uploaded_ticket(self, boleto_id, agencia_id=None):
    from celery.exceptions import SoftTimeLimitExceeded

    from apps.automation.services.ticket_parser_service import TicketParserService
    from apps.bookings.models import BoletoImportado
    from core.api import Agencia, agency_context, system_context

    if agencia_id:
        agencia = Agencia.objects.get(pk=agencia_id)
        ctx = agency_context(agencia)
    else:
        ctx = system_context()

    with ctx:
        try:
            boleto = BoletoImportado.objects.get(pk=boleto_id)

            if boleto.estado_parseo != BoletoImportado.EstadoParseo.EN_PROCESO:
                boleto.estado_parseo = BoletoImportado.EstadoParseo.EN_PROCESO
                boleto.save(update_fields=["estado_parseo"])

            logger.info(f"Iniciando procesamiento de boleto web ID: {boleto_id}")

            parser_service = TicketParserService()
            resultado = parser_service.procesar_boleto(boleto_id=boleto_id)

            if isinstance(resultado, dict) and "error" in resultado:
                logger.error(
                    f"Error lógico devuelto por el parser para el boleto {boleto_id}: {resultado['error']}"
                )
                boleto.refresh_from_db()
                boleto.estado_parseo = BoletoImportado.EstadoParseo.REVISION_REQUERIDA
                log_previo = boleto.log_parseo + " | " if boleto.log_parseo else ""
                boleto.log_parseo = f"{log_previo}Error en extracción: {resultado['error']}"
                boleto.save()
                return f"Finalizado con error lógico: {resultado['error']}"

            boleto.refresh_from_db()
            if boleto.estado_parseo == BoletoImportado.EstadoParseo.EN_PROCESO:
                boleto.estado_parseo = BoletoImportado.EstadoParseo.COMPLETADO
                boleto.save()

            logger.info(f"Boleto {boleto_id} procesado y guardado exitosamente.")
            return "Procesamiento Exitoso"

        except SoftTimeLimitExceeded:
            logger.error(
                f"❌ SoftTimeLimitExceeded: La IA tardó demasiado procesando el boleto {boleto_id}."
            )
            try:
                boleto_fallido = BoletoImportado.objects.get(pk=boleto_id)
                boleto_fallido.estado_parseo = BoletoImportado.EstadoParseo.REVISION_REQUERIDA
                log_previo = boleto_fallido.log_parseo + " | " if boleto_fallido.log_parseo else ""
                boleto_fallido.log_parseo = (
                    f"{log_previo}CRITICAL: Timeout de IA (SoftTimeLimit superado)."
                )
                boleto_fallido.save()
            except Exception as db_error:
                logger.critical(
                    f"Fallo al intentar guardar el estado de timeout para boleto {boleto_id}: {db_error}"
                )
            return "Abortado por Timeout"

        except Exception as e:
            logger.error(
                f"❌ Excepción fatal procesando el boleto {boleto_id}: {str(e)}", exc_info=True
            )
            try:
                boleto_fallido = BoletoImportado.objects.get(pk=boleto_id)
                boleto_fallido.estado_parseo = BoletoImportado.EstadoParseo.REVISION_REQUERIDA
                log_previo = boleto_fallido.log_parseo + " | " if boleto_fallido.log_parseo else ""
                boleto_fallido.log_parseo = f"{log_previo}CRASH SISTEMA: {str(e)}"
                boleto_fallido.save()
            except Exception as db_error:
                logger.critical(
                    f"Fallo al intentar guardar el estado de crash para boleto {boleto_id}: {db_error}"
                )
            raise e

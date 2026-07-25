"""Tareas asíncronas (Celery) para la aplicación automation.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, soft_time_limit=20, time_limit=30)
def process_web_uploaded_ticket(self, boleto_id, agencia_id=None):
    # process_web_uploaded_ticket: Procesa  web uploaded ticket. Args: datos a procesar. Returns: resultado procesado.
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


@shared_task(
    bind=True,
    name="core.tasks.ejecutar_cobranza_ia_task",
    max_retries=2,
    queue="default",
    soft_time_limit=300,
    time_limit=360,
)
def ejecutar_cobranza_ia_task(self):
    """
    Tarea Celery: ejecuta el comando management de cobranza IA.
    Procesa todas las facturas vencidas y envía recordatorios por WhatsApp.
    """
    import subprocess
    import sys

    from django.conf import settings

    try:
        result = subprocess.run(  # noqa: S603
            [sys.executable, "manage.py", "automated_recovery_whatsapp"],
            cwd=str(settings.BASE_DIR),
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            logger.error(f"Error ejecutando automated_recovery_whatsapp: {result.stderr}")

        logger.info(
            f"Resultado cobranza IA: {result.stdout[-500:] if result.stdout else 'Sin output'}"
        )
        return result.stdout[-1000:] if result.stdout else "Sin output"

    except subprocess.TimeoutExpired:
        logger.error("Timeout ejecutando automated_recovery_whatsapp")
        return "Timeout"
    except Exception as e:
        logger.error(f"Error ejecutando cobranza IA: {e}")
        raise self.retry(exc=e, countdown=3600) from e


@shared_task(bind=True, max_retries=2, soft_time_limit=30, time_limit=45)
def health_check_providers_task(self):
    """Ejecuta health checks de proveedores IA y claves API (programado cada 60 min)."""
    from apps.automation.providerchain.health import run_health_checks

    try:
        results = run_health_checks(force=True)
        ok = sum(1 for r in results if r["status"] == "ok")
        fail = sum(1 for r in results if r["status"] == "fail")
        logger.info("HealthCheck: %d OK, %d FAIL (total %d)", ok, fail, len(results))
        return {"ok": ok, "fail": fail, "total": len(results)}
    except Exception as e:
        logger.error("HealthCheck task failed: %s", e)
        raise self.retry(exc=e, countdown=300) from e

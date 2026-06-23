"""
Tareas asíncronas de Celery para contabilidad.
"""

import logging

from celery import shared_task
from django.core.management import call_command

from apps.common.utils.celery_utils import idempotent_task

logger = logging.getLogger(__name__)


@shared_task(time_limit=600, soft_time_limit=540)
@idempotent_task(timeout=7200, key_prefix="celery_cierre_mensual")
def cierre_mensual_task(agencia_id=None):
    from core.api import Agencia, agency_context, system_context

    try:
        if agencia_id:
            agencia = Agencia.objects.get(pk=agencia_id)
            ctx = agency_context(agencia)
        else:
            ctx = system_context()

        with ctx:
            call_command("cierre_mensual")
            logger.info("Cierre mensual ejecutado exitosamente")
            return "Cierre mensual completado"
    except Exception as e:
        logger.error(f"Error en cierre mensual: {e}")
        return f"Error: {e}"


@shared_task(
    name="core.tasks.sync_bcv_rates",
    time_limit=120,
    soft_time_limit=90,
    max_retries=3,
    default_retry_delay=300,
)
@idempotent_task(timeout=3600, key_prefix="celery_sync_bcv")
def sync_bcv_rates():
    from datetime import date

    from django.core.cache import cache

    from apps.contabilidad.models import TasaCambioBCV
    from apps.contabilidad.tasas_venezuela_client import TasasVenezuelaClient
    from apps.finance.models.currencies import Moneda, TasaCambio, TipoCambio

    logger.info("Iniciando sincronización de tasas BCV...")
    hoy = date.today()

    try:
        resultados = TasasVenezuelaClient.actualizar_tasas_db()

        if resultados.get("oficial"):
            tasa = resultados["oficial"]
            if hasattr(tasa, "tasa"):
                logger.info(f"Tasa BCV actualizada: {tasa.tasa} (Fecha: {tasa.fecha_validez})")
                return f"Sincronización exitosa. Tasa: {tasa.tasa}"
            else:
                logger.info(f"Tasa BCV actualizada (Valor Crudo): {tasa}")
                return f"Sincronización exitosa. Valor: {tasa}"
        else:
            raise ValueError(
                "No se pudo obtener/guardar la tasa oficial desde las fuentes activas."
            )

    except Exception as e:
        logger.warning(
            f"⚠️ Sincronización cambiaria falló: {e}. Activando fallback de supervivencia..."
        )

        try:
            ultima_tasa = TasaCambioBCV.objects.all().order_by("-fecha").first()
            if not ultima_tasa:
                logger.critical(
                    "❌ NO EXISTEN TASAS HISTÓRICAS EN LA BASE DE DATOS. Fallback imposible."
                )
                return f"Error: Sincronización falló y no hay histórico disponible ({e})"

            valor_tasa = ultima_tasa.tasa_bsd_por_usd

            TasaCambioBCV.objects.update_or_create(
                fecha=hoy,
                defaults={
                    "tasa_bsd_por_usd": valor_tasa,
                    "fuente": f"FALLBACK HISTÓRICO (de {ultima_tasa.fecha})",
                },
            )

            TasaCambio.objects.update_or_create(
                fecha=hoy, moneda="USD", defaults={"monto": valor_tasa}
            )

            moneda_ves = Moneda.objects.filter(codigo_iso="VES").first()
            moneda_usd = Moneda.objects.filter(codigo_iso="USD").first()
            if moneda_usd and moneda_ves:
                TipoCambio.objects.update_or_create(
                    moneda_origen=moneda_usd,
                    moneda_destino=moneda_ves,
                    fecha_efectiva=hoy,
                    defaults={"tasa_conversion": valor_tasa},
                )

            cache.delete("tasa_bcv_context")
            logger.info(
                f"🛡️ Fallback histórico aplicado exitosamente. Tasa: {valor_tasa} de la fecha: {ultima_tasa.fecha}"
            )

            import requests
            from django.conf import settings

            bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
            chat_id = getattr(settings, "TELEGRAM_FINANZAS_CHAT_ID", None) or getattr(
                settings, "TELEGRAM_GROUP_ID", None
            )

            if bot_token and chat_id:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                mensaje = (
                    f"🚨 <b>FALLO CRÍTICO - SISTEMA DE TASAS BCV</b>\n\n"
                    f"El portal del BCV y DolarApi no responden (Timeout/404).\n"
                    f"🛡️ <b>Fallback Histórico Activado Automáticamente</b>.\n"
                    f"Se ha registrado la tasa del día anterior:\n"
                    f"• <b>Tasa Aplicada:</b> {valor_tasa} BSD/USD\n"
                    f"• <b>Fecha de Origen:</b> {ultima_tasa.fecha}\n\n"
                    f"⚠️ Se requiere verificación inmediata y auditoría del staff técnico."
                )
                payload = {
                    "chat_id": chat_id,
                    "text": mensaje,
                    "parse_mode": "HTML",
                    "reply_markup": {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "✍️ Registrar Tasa Manual",
                                    "url": "https://dashboard.travelhub.com/admin/contabilidad/tasacambiobcv/",
                                }
                            ]
                        ]
                    },
                }
                try:
                    requests.post(url, json=payload, timeout=10)
                except Exception as tg_err:
                    logger.error(f"Fallo al enviar alerta interactiva a Telegram: {tg_err}")
            else:
                logger.warning("Configuración de Telegram ausente, no se pudo enviar la alerta.")

            return f"Fallback aplicado. Tasa: {valor_tasa} de {ultima_tasa.fecha}"

        except Exception as fallback_err:
            logger.exception(f"Error crítico aplicando fallback cambiario: {fallback_err}")
            return f"Error crítico: Fallback falló ({fallback_err})"


@shared_task(
    name="apps.contabilidad.tasks.ejecutar_reconciliacion_contable",
    time_limit=600,
    soft_time_limit=540,
    max_retries=3,
    default_retry_delay=300,
)
def ejecutar_reconciliacion_contable():
    """
    Tarea periódica para auditar y reconciliar asientos contables huérfanos.
    """
    from apps.contabilidad.reconciliation import ContabilidadReconciliationService

    facturas, pagos = ContabilidadReconciliationService.audit_and_reconcile()
    return {"facturas_reconciliadas": facturas, "pagos_reconciliados": pagos}

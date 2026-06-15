import logging

from celery import shared_task

from apps.common.utils.celery_utils import idempotent_task, tenant_task
from apps.communications.services.telegram_unified import enviar_alerta_telegram
from apps.finance.models import LinkDePago

logger = logging.getLogger(__name__)


@tenant_task(queue="notifications", max_retries=3, time_limit=120, soft_time_limit=90)
@idempotent_task(timeout=1800, key_prefix="celery_notif_zelle")
def notificar_pago_zelle_task(link_id, **kwargs):
    try:
        link = LinkDePago.objects.select_related("venta__cliente", "venta__agencia").get(id=link_id)
        venta = link.venta

        mensaje = (
            f"💸 *NUEVO PAGO REPORTADO*\n\n"
            f"🎫 *PNR:* {venta.localizador}\n"
            f"👤 *Cliente:* {venta.cliente.nombres.title()}\n"
            f"💰 *Monto a Conciliar:* {link.monto_total} {link.moneda}\n"
            f"🧾 *Referencia:* `{link.referencia_pago}`\n\n"
            f"⚡ *Acción Requerida:* Por favor, verifica tu estado de cuenta bancario y marca la venta como PAGADA en el Dashboard."
        )

        enviar_alerta_telegram(mensaje)
        logger.info(f"Notificación de pago enviada para Link {link_id}")
        return f"Notificación enviada (Ref: {link.referencia_pago})"

    except Exception as e:
        logger.error(f"Fallo enviando notificación de pago: {str(e)}")
        raise e


@tenant_task(
    name="apps.finance.tasks.enviar_alerta_pago_telegram_task",
    queue="notifications",
    max_retries=3,
    default_retry_delay=60,
    time_limit=120,
    soft_time_limit=90,
)
@idempotent_task(timeout=1800, key_prefix="celery_alert_pago")
def enviar_alerta_pago_telegram_task(pago_id, **kwargs):
    import requests
    from django.conf import settings

    from .models.recaudacion import Pago

    try:
        try:
            pago = Pago.objects.select_related(
                "venta", "canal_recaudacion", "agencia", "moneda"
            ).get(id_pago=pago_id)
        except Pago.DoesNotExist:
            return f"Pago {pago_id} no encontrado."

        bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        chat_id = getattr(settings, "TELEGRAM_FINANZAS_CHAT_ID", None)

        if not bot_token or not chat_id:
            return "Configuración de Telegram ausente en settings."

        localizador = (
            pago.venta.localizador.replace("-", "\\-")
            if (pago.venta and pago.venta.localizador)
            else "N/A"
        )
        monto = f"{pago.monto}".replace(".", "\\.") if pago.monto else "0\\.00"
        igtf = f"{pago.igtf_monto}".replace(".", "\\.") if pago.igtf_monto else "0\\.00"
        canal = (
            pago.canal_recaudacion.nombre.replace("-", "\\-")
            if (pago.canal_recaudacion and pago.canal_recaudacion.nombre)
            else "N/A"
        )
        agencia_nombre = (
            pago.agencia.nombre.replace("-", "\\-")
            if (pago.agencia and pago.agencia.nombre)
            else "N/A"
        )
        ref = (pago.referencia or "Ninguna").replace("-", "\\-")

        mensaje = (
            f"🚨 *CONTROL FINANCIERO \\| {agencia_nombre.upper()}*\n"
            f"===================================\n"
            f"💰 *Nuevo Pago por Verificar*\n\n"
            f"• *Localizador Venta:* `{localizador}`\n"
            f"• *Canal Receptora:* {canal} \\({pago.canal_recaudacion.get_tipo_display() if pago.canal_recaudacion else ''}\\)\n"
            f"• *Monto Cobrado:* {monto} {pago.moneda.codigo_iso if pago.moneda else ''}\n"
            f"• *IGTF Calcularizado:* Bs\\. {igtf} {'✅' if pago.igtf_aplicado else '❌'}\n"
            f"• *Referencia / Ref:* `{ref}`\n"
            f"• *Fecha Registro:* {pago.fecha_pago}\n"
            f"===================================\n"
            f"¿Autorizar la validación de fondos en cuenta?"
        )

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": mensaje,
            "parse_mode": "MarkdownV2",
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {
                            "text": "✅ Aprobar Transacción",
                            "callback_data": f"pago_appr_{pago.id_pago}",
                        },
                        {"text": "❌ Rechazar", "callback_data": f"pago_rejh_{pago.id_pago}"},
                    ]
                ]
            },
        }

        response = requests.post(url, json=payload, timeout=10)
        return f"Alerta enviada a Telegram. Status: {response.status_code}"

    except Exception as e:
        logger.error(f"Fallo enviando alerta de pago a Telegram: {str(e)}")
        raise e


@tenant_task(
    name="apps.finance.tasks.auditar_fuga_ingresos_task",
    queue="notifications",
    time_limit=300,
    soft_time_limit=270,
)
def auditar_fuga_ingresos_task(**kwargs):
    from django.utils import timezone

    from apps.bookings.models.venta import Venta
    from core.api import Agencia, agency_context, get_current_agency

    agencia_activa = get_current_agency()

    alertas = 0
    limite_tiempo = timezone.now() - timezone.timedelta(days=3)

    if agencia_activa:
        agencias = [agencia_activa]
    else:
        agencias = Agencia.objects.filter(activa=True).iterator(chunk_size=50)

    from apps.bookings.models import PagoVenta

    for agencia in agencias:
        with agency_context(agencia):
            ventas_ids = list(
                Venta.objects.filter(fecha_venta__gte=limite_tiempo)
                .exclude(estado=Venta.EstadoVenta.CANCELADA)
                .values_list("pk", flat=True)
                .iterator(chunk_size=200)
            )
            if not ventas_ids:
                continue

            ventas = Venta.objects.filter(pk__in=ventas_ids).select_related("agencia", "moneda")

            pagos_por_venta = {}
            for pago in (
                PagoVenta.objects.filter(venta_id__in=ventas_ids, confirmado=True)
                .values("venta_id", "monto")
                .iterator(chunk_size=200)
            ):
                pagos_por_venta.setdefault(pago["venta_id"], []).append(pago)

            for venta in ventas:
                total_pagado = sum(p["monto"] for p in pagos_por_venta.get(venta.pk, []))

                if venta.monto_venta_cliente > 0 and total_pagado < venta.monto_venta_cliente:
                    alertas += 1
                    diferencia = venta.monto_venta_cliente - total_pagado

                    mensaje = (
                        f"🚨 <b>ALERTA DE FUGA DE INGRESOS (Revenue Leakage)</b> 🚨\n"
                        f"===================================\n"
                        f"🎫 <b>PNR:</b> <code>{venta.localizador}</code>\n"
                        f"🏢 <b>Agencia:</b> {venta.agencia.nombre if venta.agencia else 'N/A'}\n"
                        f"💰 <b>Monto Venta Cliente:</b> $ {venta.monto_venta_cliente:.2f}\n"
                        f"💳 <b>Total Recaudado:</b> $ {total_pagado:.2f}\n"
                        f"🔥 <b>Brecha Detectada:</b> $ {diferencia:.2f}\n"
                        f"===================================\n"
                        f"Acción recomendada: Contactar al cliente o verificar conciliación contable."
                    )
                    try:
                        enviar_alerta_telegram(mensaje)
                    except Exception as e:
                        logger.error(
                            f"Error enviando alerta de fuga contable para venta {venta.id_venta}: {e}"
                        )

    return f"Auditoría de fuga concluida. Brechas detectadas: {alertas}"


@shared_task(
    name="core.tasks.check_pending_payments",
    time_limit=300,
    soft_time_limit=270,
    max_retries=2,
    default_retry_delay=600,
)
def check_pending_payments():
    from datetime import timedelta

    from django.conf import settings
    from django.core.mail import EmailMessage, get_connection
    from django.utils import timezone

    from apps.bookings.models import Venta
    from core.middleware import agency_context
    from core.models.agencia import Agencia

    logger.info("Iniciando chequeo de pagos pendientes...")
    today = timezone.now().date()
    days_to_remind = [3, 7, 15]
    count = 0

    for agencia in Agencia.objects.filter(activa=True).iterator(chunk_size=50):
        with agency_context(agencia):
            email_config = agencia.configuracion_correo
            connection = None
            from_email = settings.DEFAULT_FROM_EMAIL

            if email_config and "EMAIL_HOST" in email_config:
                try:
                    connection = get_connection(
                        host=email_config.get("EMAIL_HOST"),
                        port=email_config.get("EMAIL_PORT", 587),
                        username=email_config.get("EMAIL_HOST_USER"),
                        password=email_config.get("EMAIL_HOST_PASSWORD"),
                        use_tls=email_config.get("EMAIL_USE_TLS", True),
                    )
                    from_email = email_config.get("DEFAULT_FROM_EMAIL", from_email)
                except Exception as e:
                    logger.warning(
                        f"Error configurando SMTP personalizado para agencia {agencia.nombre}: {e}. Usando SMTP del sistema."
                    )

            for days in days_to_remind:
                target_date = today - timedelta(days=days)
                ventas_pendientes = Venta.objects.filter(
                    agencia=agencia,
                    fecha_venta__date=target_date,
                    saldo_pendiente__gt=0,
                    estado__in=[Venta.EstadoVenta.PENDIENTE_PAGO, Venta.EstadoVenta.PAGADA_PARCIAL],
                    cliente__email__isnull=False,
                ).select_related("cliente", "moneda")

                for venta in ventas_pendientes.iterator(chunk_size=200):
                    try:
                        cliente = venta.cliente
                        sender_name = agencia.nombre_comercial or agencia.nombre
                        subject = (
                            f"Recordatorio de Pago Pendiente - Localizador: {venta.localizador}"
                        )
                        body = (
                            f"Estimado/a {cliente.nombres},\n\n"
                            f"Desde {sender_name} le recordamos que su reserva con localizador {venta.localizador} tiene un saldo pendiente de {venta.saldo_pendiente} {venta.moneda.codigo_iso}.\n\n"
                            "Por favor, realice el pago para evitar la cancelación de sus servicios.\n\n"
                            "Saludos,\nEl equipo de Administración"
                        )

                        email = EmailMessage(
                            subject, body, from_email, [cliente.email], connection=connection
                        )
                        email.send()

                        count += 1
                        logger.info(
                            f"Recordatorio enviado para Venta {venta.id_venta} (Agencia: {agencia.nombre})"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error enviando recordatorio para Venta {venta.id_venta}: {e}"
                        )

    return f"Recordatorios de pago enviados: {count}"


@tenant_task(
    name="core.tasks.procesar_facturacion_masiva_task",
    time_limit=600,
    soft_time_limit=540,
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
)
@idempotent_task(timeout=7200, key_prefix="celery_facturacion_masiva")
def procesar_facturacion_masiva_task(boleto_ids, cliente_id, **kwargs):
    from apps.bookings.models import BoletoImportado
    from apps.crm.models import Cliente
    from apps.finance.services.invoice_service import InvoiceService

    logger.info(
        f"🚀 Iniciando facturación masiva asíncrona para {len(boleto_ids)} boletos y cliente ID {cliente_id}"
    )

    try:
        cliente = Cliente.objects.select_related("agencia").get(pk=cliente_id)
        queryset = BoletoImportado.objects.filter(pk__in=boleto_ids).select_related(
            "agencia", "proveedor", "venta_asociada"
        )

        results = InvoiceService.mass_assign_and_invoice(queryset, cliente)
        logger.info(f"✅ Facturación masiva completada: {len(results)} registros procesados.")
        return results
    except Exception as e:
        logger.error(f"❌ Error fatal en procesar_facturacion_masiva_task: {e}")
        raise e


@shared_task(
    name="core.tasks.create_invoice_from_sale_task",
    time_limit=300,
    soft_time_limit=240,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
@idempotent_task(timeout=3600, key_prefix="celery_create_invoice")
def create_invoice_from_sale_task(venta_id):
    from apps.finance.services.invoice_service import InvoiceService

    logger.info(f"📩 Generando factura automática para Venta {venta_id}")
    try:
        InvoiceService.create_invoice_from_sale(venta_id)
        logger.info(f"✅ Factura automática creada para Venta {venta_id}")
    except Exception as e:
        logger.error(f"❌ Error creando factura para Venta {venta_id}: {e}")
        raise

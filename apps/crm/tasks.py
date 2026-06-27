import base64
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="core.tasks.check_passport_expiry",
    time_limit=300,
    soft_time_limit=270,
    max_retries=2,
    default_retry_delay=600,
)
def check_passport_expiry():
    from datetime import timedelta

    from django.conf import settings
    from django.core.mail import send_mail
    from django.utils import timezone

    from apps.crm.models import Cliente, Pasajero
    from core.middleware import agency_context
    from core.models.agencia import Agencia

    logger.info("Iniciando chequeo de vencimiento de documentos (Multi-Tenant)...")

    today = timezone.now().date()
    threshold_date = today + timedelta(days=180)  # 6 meses

    start_range = threshold_date
    end_range = threshold_date + timedelta(days=7)

    total_alerts = 0

    for agencia in Agencia.objects.filter(activa=True).iterator(chunk_size=50):
        with agency_context(agencia):
            pasajeros_vencimiento = Pasajero.objects.filter(
                agencia=agencia,
                tipo_documento=Pasajero.TipoDocumentoChoices.PASAPORTE,
                fecha_vencimiento_documento__range=[start_range, end_range],
            )

            clientes_vencimiento = Cliente.objects.filter(
                agencia=agencia,
                numero_pasaporte__isnull=False,
                fecha_expiracion_pasaporte__range=[start_range, end_range],
            )

            count = pasajeros_vencimiento.count() + clientes_vencimiento.count()

        if count > 0:
            logger.info(f"Agencia {agencia.nombre}: {count} documentos por vencer.")

            report_lines = [
                f"Reporte para {agencia.nombre_comercial or agencia.nombre}:\nLos siguientes documentos vencerán en 6 meses:\n"
            ]

            for p in pasajeros_vencimiento.iterator(chunk_size=200):
                report_lines.append(
                    f"- Pasajero: {p.nombres} {p.apellidos} (Vence: {p.fecha_vencimiento_documento})"
                )

            for c in clientes_vencimiento.iterator(chunk_size=200):
                report_lines.append(
                    f"- Cliente: {c.nombres} {c.apellidos} (Vence: {c.fecha_expiracion_pasaporte})"
                )

            body = "\n".join(report_lines)

            recipient_email = (
                agencia.email_ventas
                or agencia.email_soporte
                or getattr(settings, "TICKET_NOTIFICATION_RECIPIENT", settings.EMAIL_HOST_USER)
            )

            if recipient_email:
                send_mail(
                    "⚠️ Alerta de Vencimiento de Pasaportes",
                    body,
                    agencia.email_principal or settings.DEFAULT_FROM_EMAIL,
                    [recipient_email],
                    fail_silently=False,
                )
                logger.info(f"Reporte enviado a {recipient_email}")
                total_alerts += count

    return f"Chequeo completado. {total_alerts} alertas procesadas."


@shared_task(
    name="core.tasks.check_client_birthdays",
    time_limit=300,
    soft_time_limit=270,
    max_retries=2,
    default_retry_delay=600,
)
def check_client_birthdays():
    from django.conf import settings
    from django.core.mail import EmailMessage, get_connection
    from django.utils import timezone

    from apps.crm.models import Cliente
    from core.middleware import agency_context
    from core.models.agencia import Agencia

    logger.info("Iniciando chequeo de cumpleaños (Multi-Tenant)...")
    today = timezone.now().date()
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
                    logger.error(f"Error configurando SMTP para agencia {agencia.nombre}: {e}")
                    continue
            else:
                connection = get_connection()

            clientes_cumple = Cliente.objects.filter(
                agencia=agencia,
                fecha_nacimiento__month=today.month,
                fecha_nacimiento__day=today.day,
                email__isnull=False,
            )

        for c in clientes_cumple.iterator(chunk_size=200):
            try:
                email = EmailMessage(
                    f"¡Feliz Cumpleaños, {c.nombres}!",
                    f"Hola {c.nombres},\n\nDesde {agencia.nombre_comercial or agencia.nombre} te deseamos un muy feliz cumpleaños. ¡Que tengas un día lleno de viajes y aventuras!\n\nSaludos,\nEl equipo de {agencia.nombre}",
                    from_email,
                    [c.email],
                    connection=connection,
                )
                email.send()
                count += 1
            except Exception as e:
                logger.error(
                    f"Error enviando felicitación a cliente {c.id_cliente} de agencia {agencia.nombre}: {e}"
                )

    logger.info(f"Felicitaciones enviadas (Total): {count}")
    return f"Cumpleaños procesados: {count}"


@shared_task(
    name="core.tasks.task_ocr_passport_fast",
    queue="ia_fast",
    time_limit=60,
    soft_time_limit=50,
    max_retries=2,
    default_retry_delay=30,
)
def task_ocr_passport_fast(file_content_base64: str, mime_type: str = "image/jpeg"):
    from apps.automation.services.ocr_service import ocr_service

    try:
        logger.info("Iniciando tarea de OCR rapida para Pasaporte (IA_FAST)")
        content = base64.b64decode(file_content_base64)
        resultado = ocr_service.procesar_pasaporte(content, mime_type)
        return resultado
    except Exception as e:
        logger.error(f"Error en task_ocr_passport_fast: {e}")


@shared_task(
    name="core.tasks.process_passport_ocr",
    queue="ia_fast",
    time_limit=120,
    soft_time_limit=100,
    max_retries=2,
    default_retry_delay=30,
)
def process_passport_ocr(pasaporte_id):
    from apps.automation.services.passport_ocr_service import PassportOCRService
    from apps.crm.models import PasaporteEscaneado
    from core.signals_bypass import disable_signals

    try:
        instance = PasaporteEscaneado.objects.get(pk=pasaporte_id)
    except PasaporteEscaneado.DoesNotExist:
        logger.error(f"PasaporteEscaneado {pasaporte_id} no encontrado")
        return

    if instance.numero_pasaporte:
        logger.info(f"PasaporteEscaneado {pasaporte_id} ya tiene datos OCR, omitiendo")
        return

    try:
        ocr_service = PassportOCRService()
        result = ocr_service.process_passport_image(instance.imagen_original)

        if result["success"]:
            data = result["data"]
            json_safe_data = {}
            for key, value in data.items():
                if hasattr(value, "strftime"):
                    json_safe_data[key] = value.strftime("%Y-%m-%d")
                else:
                    json_safe_data[key] = value

            with disable_signals():
                instance.numero_pasaporte = data.get("numero_pasaporte", "")
                instance.nombres = data.get("nombres", "")
                instance.apellidos = data.get("apellidos", "")
                instance.nacionalidad = data.get("nacionalidad", "")
                instance.fecha_nacimiento = data.get("fecha_nacimiento")
                instance.fecha_vencimiento = data.get("fecha_vencimiento")
                instance.sexo = data.get("sexo", "")
                instance.confianza_ocr = result["confidence"]
                instance.datos_ocr_completos = json_safe_data
                instance.texto_mrz = data.get("texto_mrz", "")
                instance.save(
                    update_fields=[
                        "numero_pasaporte",
                        "nombres",
                        "apellidos",
                        "nacionalidad",
                        "fecha_nacimiento",
                        "fecha_vencimiento",
                        "sexo",
                        "confianza_ocr",
                        "datos_ocr_completos",
                        "texto_mrz",
                    ]
                )
            logger.info(f"OCR completado para PasaporteEscaneado {pasaporte_id}")
    except Exception as e:
        logger.error(f"Error procesando pasaporte {pasaporte_id}: {e}")

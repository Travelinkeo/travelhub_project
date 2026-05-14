# core/tasks.py
import logging
import os
from email.header import decode_header

from celery import shared_task
from django.conf import settings

from apps.common.utils.celery_utils import tenant_task
from core.middleware import agency_context

logger = logging.getLogger(__name__)

def get_filename_from_header(header):
    """Decodifica el nombre de un archivo desde el header de un email."""
    if not header:
        return None
    decoded_header = decode_header(header)
    parts = []
    for part, charset in decoded_header:
        if isinstance(part, bytes):
            try:
                parts.append(part.decode(charset or 'utf-8', errors='ignore'))
            except (UnicodeDecodeError, LookupError):
                parts.append(part.decode('latin-1', errors='ignore'))
        else:
            parts.append(part)
    return ''.join(parts)


@shared_task(
    name="core.tasks.process_incoming_emails",
    time_limit=600,
    soft_time_limit=540,
    max_retries=3,
    default_retry_delay=300,
    acks_late=True,
)
def process_incoming_emails():
    """
    ⚡ ASÍNCRONO | 🏢 MULTI-TENANT
    Daemon orquestador tipo Cron que inspecciona los correos de todas las agencias activas buscando boletos para auto-parseo.
    
    ¿Por qué?: En un modelo SaaS, no podemos requerir procesos bloqueando el servidor HTTP esperando IMAP.
    Esta tarea se ejecuta silenciosamente. Usamos `process_all=False` para procesar por lotes (batches controlados) 
    y evitar crashes de memoria (OOM) si una agencia inunda repentinamente la bandeja con 10,000 correos atrasados.
    """
    from apps.communications.services.email_monitor_service import EmailMonitorService
    from core.models.agencia import Agencia

    logger.info("🚀 Iniciando tarea programada: Procesamiento de Correos (Multi-Tenant)")
    
    # SaaS: Buscar todas las agencias activas con configuración de correo
    agencias = Agencia.objects.filter(
        activa=True
    ).exclude(
        configuracion__correo_emisiones__isnull=True
    ).exclude(
        configuracion__correo_emisiones__exact=''
    )
    total_procesados = 0
    total_agencias = 0

    if not agencias.exists():
        logger.warning("No hay agencias activas para monitorear.")
        return "Sin agencias activas."

    for agencia in agencias:
        try:
            # Validar si tiene credenciales SaaS configuradas (en componente configuración)
            config = agencia.configuracion
            if not config or not config.correo_emisiones or not config.password_app_correo:
                continue

            with agency_context(agencia):
                logger.info(f"🔄 Procesando agencia SaaS: {agencia.nombre} ({config.correo_emisiones})")
                
                monitor = EmailMonitorService(
                    agencia=agencia, 
                    notification_type='telegram', 
                    process_all=False, 
                    mark_as_read=True
                )
                
                # Procesar una vez (sin loop infinito)
                cantidad = monitor.procesar_una_vez()
                total_procesados += cantidad
                total_agencias += 1
            
        except Exception as e:
            logger.error(f"❌ Error procesando agencia {agencia.nombre}: {e}")
            continue

    resultado = f"Tarea finalizada. {total_procesados} correos procesados en {total_agencias} agencias."
    logger.info(resultado)
    return resultado


@tenant_task(
    name="core.tasks.parsear_boleto_individual",
    time_limit=300,
    soft_time_limit=270,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def parsear_boleto_individual(boleto_id, **kwargs):
    """
    Tarea asíncrona para procesar un boleto individual.
    Útil para uploads desde Admin o reintentos manuales.
    """
    from apps.bookings.models import BoletoImportado

    try:
        boleto = BoletoImportado.objects.get(pk=boleto_id)
        if boleto.estado_parseo in (BoletoImportado.EstadoParseo.COMPLETADO, BoletoImportado.EstadoParseo.ERROR_PARSEO):
            logger.info(f"⏭️ Boleto {boleto_id} ya fue procesado (estado: {boleto.estado_parseo}). Omitiendo.")
            return f"Boleto {boleto_id} ya procesado previamente."
    except BoletoImportado.DoesNotExist:
        return f"Boleto {boleto_id} no existe."

    try:
        from apps.automation.services.ticket_parser_service import TicketParserService
        logger.info(f"🧩 Iniciando tarea de parseo para Boleto {boleto_id} (Params: {kwargs})")
        service = TicketParserService()
        resultado = service.procesar_boleto(
            boleto_id, 
            ignore_manual=kwargs.get('ignore_manual', False),
            bypass_cache=kwargs.get('bypass_cache', False)
        )
        if resultado:
             logger.info(f"✅ Tarea de parseo completada para Boleto {boleto_id}")
             return f"Boleto {boleto_id} procesado exitosamente."
        else:
             logger.warning(f"⚠️ Tarea de parseo finalizó sin resultados para Boleto {boleto_id}")
             return f"Fallo al procesar Boleto {boleto_id}"
    except Exception as e:
        logger.error(f"❌ Error en parsear_boleto_individual: {e}")
        return f"Error: {e}"


@shared_task(
    name="core.tasks.retry_queued_boletos",
    time_limit=300,
    soft_time_limit=270,
    max_retries=2,
    default_retry_delay=600,
)
def retry_queued_boletos():
    """
    🚨 CRÍTICO | ⚡ ASÍNCRONO
    Sistema de Recuperación (Auto-Healing) para la cola de Celery/Redis.
    
    ¿Por qué?: A veces Redis pierde conexión, sufre OOM o el entorno se reinicia abruptamente mientras 
    un lote GDS masivo entraba por Webhooks/Email. Los boletos quedan marcados en DB como 'QUE' eternamente 
    y el ERP del cliente se paraliza.
    Este Cron los escanea y usa `safe_delay` para reencolarlos sin crear "recursión infinita" 
    con las colas (una práctica que haría explotar a RabbitMQ o Redis subyacente).
    """
    from apps.bookings.models import BoletoImportado

    from apps.common.utils.celery_utils import safe_delay
    
    boletos_en_espera = BoletoImportado.objects.filter(estado_parseo='QUE')
    if not boletos_en_espera.exists():
        return "No hay boletos en espera de cola."
        
    count = 0
    for boleto in boletos_en_espera:
        # Intentamos encolar de nuevo usando el helper seguro
        # No usamos el mismo task para evitar recursión infinita
        task = safe_delay(parsear_boleto_individual, boleto.id_boleto_importado)
        if task:
            # Si se encoló, actualizamos el estado a PRO
            boleto.estado_parseo = 'PRO'
            boleto.log_parseo = f"Re-encolado automáticamente por sistema de recuperación. TaskID: {task.id}"
            boleto.save(update_fields=['estado_parseo', 'log_parseo'])
            count += 1
            
    return f"Se re-encolaron {count} boletos que estaban en espera."


    

    

@tenant_task(
    name="core.tasks.send_ticket_notification",
    time_limit=120,
    soft_time_limit=90,
    max_retries=3,
    default_retry_delay=120,
    acks_late=True,
)
def send_ticket_notification(boleto_id, **kwargs):

    """
    Envía una notificación por correo electrónico con el boleto PDF generado.
    """
    from apps.bookings.models import BoletoImportado

    try:
        boleto = BoletoImportado.objects.get(id_boleto_importado=boleto_id)
        if hasattr(boleto, 'notificacion_enviada') and boleto.notificacion_enviada:
            logger.info(f"⏭️ Notificación ya enviada para Boleto {boleto_id}. Omitiendo.")
            return f"Notificación ya enviada para boleto {boleto_id}."
    except BoletoImportado.DoesNotExist:
        return f"Boleto con ID {boleto_id} no encontrado."

    try:
        from django.core.mail import EmailMessage

        
        logger.info(f"Iniciando envío de notificación para Boleto ID: {boleto_id}")

        if not boleto.archivo_pdf_generado:
            logger.warning(f"No se encontró PDF generado para el Boleto ID: {boleto_id}. No se puede enviar notificación.")
            return f"No hay PDF para el boleto {boleto_id}."

        # Priorizar email del cliente asociado
        recipient_email = boleto.cliente.email if boleto.cliente else None
        if not recipient_email:
            logger.error(f"El boleto {boleto_id} no tiene cliente con email. No se puede enviar notificación.")
            return "Destinatario no encontrado."

        # 🛡️ Guard: Skip placeholder emails
        if "@sin-email.com" in recipient_email.lower():
            logger.info(f"🔕 Notificación omitida para email de marcador de posición: {recipient_email}")
            return "Omitido por ser email de marcador de posición"

        sender_name = boleto.agencia.nombre_comercial or boleto.agencia.nombre
        subject = f"Nuevo Boleto Procesado: {boleto.nombre_pasajero_completo} - PNR: {boleto.localizador_pnr}"

        body = (
            "Se ha procesado un nuevo boleto de viaje.\n\n"
            f"Pasajero: {boleto.nombre_pasajero_completo}\n"
            f"Localizador: {boleto.localizador_pnr}\n"
            f"Ruta: {boleto.ruta_vuelo}\n\n"
            "El boleto unificado se encuentra adjunto a este correo.\n\n"
            f"Saludos,\nEl equipo de {sender_name}"
        )

        email = EmailMessage(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
        )

        # Adjuntar el PDF
        boleto.archivo_pdf_generado.open(mode='rb')
        email.attach(
            os.path.basename(boleto.archivo_pdf_generado.name),
            boleto.archivo_pdf_generado.read(),
            'application/pdf'
        )
        boleto.archivo_pdf_generado.close()

        email.send()
        logger.info(f"Notificación para Boleto ID: {boleto_id} enviada a {recipient_email}.")
        return f"Notificación para boleto {boleto_id} enviada."

    except BoletoImportado.DoesNotExist:
        logger.error(f"Se intentó enviar una notificación para un Boleto ID ({boleto_id}) que no existe.")
        return f"Boleto con ID {boleto_id} no encontrado."
    except Exception as e:
        logger.exception(f"Fallo crítico al enviar notificación para Boleto ID {boleto_id}: {e}")
        raise e


@shared_task(
    name="core.tasks.check_passport_expiry",
    time_limit=300,
    soft_time_limit=270,
    max_retries=2,
    default_retry_delay=600,
)
def check_passport_expiry():
    """
    Tarea diaria para verificar pasaportes próximos a vencer (6 meses).
    Envía una alerta al agente (o cliente en el futuro).
    """
    from datetime import timedelta

    from django.core.mail import send_mail
    from django.utils import timezone

    from apps.crm.models import Cliente, Pasajero
    
    logger.info("Iniciando chequeo de vencimiento de documentos (Multi-Tenant)...")
    
    today = timezone.now().date()
    threshold_date = today + timedelta(days=180) # 6 meses
    
    # Buscar pasaportes que vencen en el rango de la semana objetivo
    start_range = threshold_date
    end_range = threshold_date + timedelta(days=7)
    
    from core.models.agencia import Agencia
    total_alerts = 0

    # Iterar por agencia para enviar reportes separados
    for agencia in Agencia.objects.filter(activa=True):
        with agency_context(agencia):
            pasajeros_vencimiento = Pasajero.objects.filter(
                agencia=agencia,
                tipo_documento=Pasajero.TipoDocumentoChoices.PASAPORTE,
                fecha_vencimiento_documento__range=[start_range, end_range]
            )
            
            clientes_vencimiento = Cliente.objects.filter(
                agencia=agencia,
                numero_pasaporte__isnull=False,
                fecha_expiracion_pasaporte__range=[start_range, end_range]
            )
            
            count = pasajeros_vencimiento.count() + clientes_vencimiento.count()
        
        if count > 0:
            logger.info(f"Agencia {agencia.nombre}: {count} documentos por vencer.")
            
            report_lines = [f"Reporte para {agencia.nombre_comercial or agencia.nombre}:\nLos siguientes documentos vencerán en 6 meses:\n"]
            
            for p in pasajeros_vencimiento:
                report_lines.append(f"- Pasajero: {p.nombres} {p.apellidos} (Vence: {p.fecha_vencimiento_documento})")
                
            for c in clientes_vencimiento:
                report_lines.append(f"- Cliente: {c.nombres} {c.apellidos} (Vence: {c.fecha_expiracion_pasaporte})")
                
            body = "\n".join(report_lines)
            
            recipient_email = agencia.email_ventas or agencia.email_soporte or getattr(settings, 'TICKET_NOTIFICATION_RECIPIENT', settings.EMAIL_HOST_USER)
            
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
    name="core.tasks.check_upcoming_flights",
    time_limit=300,
    soft_time_limit=270,
    max_retries=2,
    default_retry_delay=600,
)
def check_upcoming_flights():
    """
    🏢 MULTI-TENANT | ⚡ ASÍNCRONO
    Busca vuelos pautados para las próximas 24 horas y envía "Recordatorios de Check-In".
    
    ¿Por qué?: Valor agregado premium (Concierge mode). En vez de que el agente humano 
    revise reportes a mano en Excel para atender a sus clientes Vip, nuestro scraper 
    detecta los PNR críticos (que están marcados como Finalizados en el JSON estructurado)
    y alerta en el Grupo interno de Telegram. Así, el agente entra al GDS y factura antes.
    """
    import json
    from datetime import timedelta

    from django.utils import timezone

    from apps.bookings.models import BoletoImportado
    
    logger.info("🔍 Buscando vuelos próximos para Check-in...")
    
    now = timezone.now()
    tomorrow_start = now + timedelta(hours=23)
    
    # Buscamos boletos con fecha de salida en el rango de ~24hs
    # Nota: Esto depende de que hayamos parseado la fecha de salida.
    # Como el modelo BoletoImportado actual guarda mucha data en JSON, 
    # iteraremos los recientes para verificar la fecha dentro del JSON 'datos_parseados'.
    
    # Optimización: Filtrar por fecha de creación reciente (últimos 365 días)
    # y que no estén cancelados.
    from apps.communications.services.telegram_notification_service import (
        TelegramNotificationService,
    )
    from core.models.agencia import Agencia
    
    total_alerts = 0
    
    # Iterar por Agencias
    for agencia in Agencia.objects.filter(activa=True):
        with agency_context(agencia):
            boletos = BoletoImportado.objects.filter(
                agencia=agencia,
                fecha_subida__gte=now - timedelta(days=365),
                estado_parseo='COM',
                # Optimización DB: Filtrado rápido a nivel de string JSON antes de cargar a memoria Python
                datos_parseados__icontains=tomorrow_start.strftime("%d %b").upper()
            )
        
        # Obtener Chat ID de la agencia (SaaS)
        chat_id = agencia.configuracion_api.get('TELEGRAM_GROUP_ID') or getattr(settings, 'TELEGRAM_GROUP_ID', None)
        if not chat_id:
            continue

        for boleto in boletos:
            try:
                data = boleto.datos_parseados
                if isinstance(data, str):
                    data = json.loads(data)
                    
                # Buscar segmentos de vuelo
                if 'vuelos' in data and isinstance(data['vuelos'], list):
                    for vuelo in data['vuelos']:
                        fecha_str = vuelo.get('fecha_salida') or vuelo.get('date')
                        
                        target_date_str = tomorrow_start.strftime("%d %b") 
                        
                        if fecha_str and target_date_str.upper() in str(fecha_str).upper():
                            # ENCONTRADO CANDIDATO
                            msg = (
                                f"⏰ <b>RECORDATORIO DE CHECK-IN</b>\n\n"
                                f"El vuelo de <b>{boleto.nombre_pasajero_completo}</b> sale mañana.\n"
                                f"✈️ Aerolínea: {boleto.aerolinea_emisora}\n"
                                f"📍 PNR: <code>{boleto.localizador_pnr}</code>\n"
                                f"📅 Fecha: {fecha_str}\n\n"
                                f"<i>Verifica si el Check-in está abierto.</i>"
                            )
                            # Enviar usando servicio SaaS con contexto de Agencia
                            TelegramNotificationService.send_message(msg, chat_id=chat_id, agencia=agencia)
                            total_alerts += 1
                            logger.info(f"Alerta check-in enviada para {boleto.localizador_pnr} (Agencia: {agencia.nombre})")
                            break 
                            
            except Exception as e:
                logger.error(f"Error procesando boleto {boleto.pk} para checkin: {e}")

    result = f"Check-in scan completado. Alertas enviadas: {total_alerts}"
    logger.info(result)
    return result


@shared_task(
    name="core.tasks.check_client_birthdays",
    time_limit=300,
    soft_time_limit=270,
    max_retries=2,
    default_retry_delay=600,
)
def check_client_birthdays():
    """
    Tarea diaria para felicitar a clientes y pasajeros por su cumpleaños.
    Soporta configuración Multi-Tenant (SMTP por Agencia).
    """
    from django.core.mail import EmailMessage, get_connection
    from django.utils import timezone

    from apps.crm.models import Cliente
    from core.models.agencia import Agencia
    
    logger.info("Iniciando chequeo de cumpleaños (Multi-Tenant)...")
    today = timezone.now().date()
    count = 0
    
    # Iterar por cada agencia activa
    for agencia in Agencia.objects.filter(activa=True):
        with agency_context(agencia):
            # Obtener configuración de correo de la agencia
            email_config = agencia.configuracion_correo
            
            # Si no tiene configuración, usar la del sistema (fallback) o saltar
            # Por ahora, usaremos un connection con los datos si existen
            connection = None
            from_email = settings.DEFAULT_FROM_EMAIL
            
            if email_config and 'EMAIL_HOST' in email_config:
                try:
                    connection = get_connection(
                        host=email_config.get('EMAIL_HOST'),
                        port=email_config.get('EMAIL_PORT', 587),
                        username=email_config.get('EMAIL_HOST_USER'),
                        password=email_config.get('EMAIL_HOST_PASSWORD'),
                        use_tls=email_config.get('EMAIL_USE_TLS', True)
                    )
                    from_email = email_config.get('DEFAULT_FROM_EMAIL', from_email)
                except Exception as e:
                    logger.error(f"Error configurando SMTP para agencia {agencia.nombre}: {e}")
                    continue # Saltar esta agencia si falla la config
            else:
                # Usar conexión por defecto de Django
                connection = get_connection()

            # Buscar clientes de ESTA agencia que cumplen años
            clientes_cumple = Cliente.objects.filter(
                agencia=agencia,
                fecha_nacimiento__month=today.month,
                fecha_nacimiento__day=today.day,
                email__isnull=False
            )
        
        # Enviar a Clientes
        for c in clientes_cumple:
            try:
                email = EmailMessage(
                    f"¡Feliz Cumpleaños, {c.nombres}!",
                    f"Hola {c.nombres},\n\nDesde {agencia.nombre_comercial or agencia.nombre} te deseamos un muy feliz cumpleaños. ¡Que tengas un día lleno de viajes y aventuras!\n\nSaludos,\nEl equipo de {agencia.nombre}",
                    from_email,
                    [c.email],
                    connection=connection
                )
                email.send()
                count += 1
            except Exception as e:
                logger.error(f"Error enviando felicitación a cliente {c.id_cliente} de agencia {agencia.nombre}: {e}")

    logger.info(f"Felicitaciones enviadas (Total): {count}")
    return f"Cumpleaños procesados: {count}"


@shared_task(
    name="core.tasks.check_pending_payments",
    time_limit=300,
    soft_time_limit=270,
    max_retries=2,
    default_retry_delay=600,
)
def check_pending_payments():
    """
    Tarea diaria para recordar pagos pendientes.
    Regla: Recordar a los 3, 7 y 15 días de la venta si hay saldo pendiente.
    """
    from datetime import timedelta

    from django.core.mail import EmailMessage, get_connection
    from django.utils import timezone

    from apps.bookings.models import Venta
    
    logger.info("Iniciando chequeo de pagos pendientes...")
    today = timezone.now().date()
    
    # Definir los días de antigüedad para enviar recordatorio
    days_to_remind = [3, 7, 15]
    
    count = 0
    
    from core.models.agencia import Agencia

    for agencia in Agencia.objects.filter(activa=True):
        with agency_context(agencia):
            # Configurar SMTP de agencia
            email_config = agencia.configuracion_correo
            connection = None
            from_email = settings.DEFAULT_FROM_EMAIL
            
            if email_config and 'EMAIL_HOST' in email_config:
                try:
                    connection = get_connection(
                        host=email_config.get('EMAIL_HOST'),
                        port=email_config.get('EMAIL_PORT', 587),
                        username=email_config.get('EMAIL_HOST_USER'),
                        password=email_config.get('EMAIL_HOST_PASSWORD'),
                        use_tls=email_config.get('EMAIL_USE_TLS', True)
                    )
                    from_email = email_config.get('DEFAULT_FROM_EMAIL', from_email)
                except Exception as e:
                    logger.warning(f"Error configurando SMTP personalizado para agencia {agencia.nombre}: {e}. Usando SMTP del sistema.")
            
            for days in days_to_remind:
                target_date = today - timedelta(days=days)
                
                # Buscar ventas de ESTA agencia
                ventas_pendientes = Venta.objects.filter(
                    agencia=agencia,
                    fecha_venta__date=target_date,
                    saldo_pendiente__gt=0,
                    estado__in=[Venta.EstadoVenta.PENDIENTE_PAGO, Venta.EstadoVenta.PAGADA_PARCIAL],
                    cliente__email__isnull=False
                )
                
                for venta in ventas_pendientes:
                    try:
                        cliente = venta.cliente
                        sender_name = agencia.nombre_comercial or agencia.nombre
                        subject = f"Recordatorio de Pago Pendiente - Localizador: {venta.localizador}"
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
                        logger.info(f"Recordatorio enviado para Venta {venta.id_venta} (Agencia: {agencia.nombre})")
                        
                    except Exception as e:
                        logger.error(f"Error enviando recordatorio para Venta {venta.id_venta}: {e}")
                
    return f"Recordatorios de pago enviados: {count}"


@shared_task(
    name="core.tasks.sync_bcv_rates",
    time_limit=120,
    soft_time_limit=90,
    max_retries=3,
    default_retry_delay=300,
)
def sync_bcv_rates():
    """
    Tarea diaria para sincronizar la tasa del BCV.
    """
    from apps.contabilidad.tasas_venezuela_client import TasasVenezuelaClient
    
    logger.info("Iniciando sincronización de tasas BCV...")
    
    try:
        resultados = TasasVenezuelaClient.actualizar_tasas_db()
        
        if resultados.get('oficial'):
            tasa = resultados['oficial']
            # Verificar si es objeto valido (tiene atributo tasa) o es un bool/dict
            if hasattr(tasa, 'tasa'):
                logger.info(f"Tasa BCV actualizada: {tasa.tasa} (Fecha: {tasa.fecha_validez})")
                return f"Sincronización exitosa. Tasa: {tasa.tasa}"
            else:
                 logger.info(f"Tasa BCV actualizada (Valor Crudo): {tasa}")
                 return f"Sincronización exitosa. Valor: {tasa}"
        else:
            logger.error("No se pudo obtener/guardar la tasa BCV.")
            return "Fallo en sincronización BCV."
            
    except Exception as e:
        logger.exception(f"Error crítico sincronizando tasas: {e}")
        return f"Error crítico: {e}"


@tenant_task(name="core.tasks.enviar_notificacion_whatsapp_task", bind=True, max_retries=3)
def enviar_notificacion_whatsapp_task(self, numero_cliente, mensaje, email_cliente=None, media_url=None, file_name=None, **kwargs):
    """
    🚨 CRÍTICO | ⚡ ASÍNCRONO
    Patrón Resiliente con Dead Letter Queue para envíos por Evolution/Meta API.
    """
    from django.core.mail import send_mail

    from apps.communications.services.telegram_unified import enviar_alerta_telegram
    from apps.communications.services.whatsapp_unified import send_whatsapp_message
    from core.middleware import get_current_agency
    agencia = get_current_agency()

    agencia_nombre = agencia.nombre if agencia else "TravelHub"

    try:
        # 1. INTENTO PRINCIPAL: Enviar por el sistema unificado (Evolution -> Meta)
        logger.info(f"Intentando enviar WhatsApp a {numero_cliente} (Intento {self.request.retries + 1}/4)")
        
        respuesta = send_whatsapp_message(
            number=numero_cliente, 
            text=mensaje, 
            agencia=agencia,
            media_url=media_url,
            file_name=file_name
        )
        
        if not respuesta.get('success'):
            raise Exception(f"WhatsApp Error: {respuesta.get('error_message', 'Unknown Error')}")
            
        logger.info(f"✅ WhatsApp enviado exitosamente a {numero_cliente} via {respuesta.get('provider')}")
        return "Notificación enviada"

    except Exception as exc:
        # 2. SISTEMA DE REINTENTOS ESCALONADOS
        retrasos_escalonados = [300, 900, 3600] 
        
        if self.request.retries < self.max_retries:
            tiempo_espera = retrasos_escalonados[self.request.retries]
            raise self.retry(exc=exc, countdown=tiempo_espera) from exc
        else:
            # 3. DEAD LETTER QUEUE (FALLBACK DEFINITIVO)
            logger.error(f"❌ Fallo definitivo enviando WhatsApp a {numero_cliente}.")
            
            # A. Notificar al Agente por Telegram
            alerta_agencia = (
                f"🚨 *FALLO WHATSAPP - {agencia_nombre}*\n\n"
                f"No se pudo entregar el mensaje a *{numero_cliente}*.\n"
                f"Detalle: {str(exc)}\n"
            )
            enviar_alerta_telegram(alerta_agencia)
            
            # B. Enviar correo de respaldo
            if email_cliente:
                try:
                    send_mail(
                        subject=f"Información de tu viaje - {agencia_nombre}",
                        message=f"Hola,\n\nIntentamos enviarte esta información por WhatsApp pero no fue posible. Aquí tienes los detalles:\n\n{mensaje}\n\nSaludos,\nEl equipo de {agencia_nombre}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email_cliente],
                        fail_silently=True
                    )
                except Exception as e:
                    logger.warning(f"Error sending fallback email to {email_cliente}: {e}")
            
            return "Fallo definitivo - Fallback ejecutado"


@shared_task(
    name="core.tasks.task_ocr_passport_fast",
    queue='ia_fast',
    time_limit=60,
    soft_time_limit=50,
    max_retries=2,
    default_retry_delay=30,
)
def task_ocr_passport_fast(file_content_base64: str, mime_type: str = "image/jpeg"):
    """
    🧠 IA / GOD MODE | ⚡ ASÍNCRONO (Priority Queue)
    Extracción de datos OCR de latencia ultra baja para escanear MRZ de Pasaportes de forma autónoma.
    
    Args:
        file_content_base64 (str): Base64 crudo emitido del JS Scanner del lado Frontend.
        mime_type (str): Para inyecciones Vision correctas al LLM (Gemini 1.5).
        
    Returns:
        Dict: Estructura tipada con nombres, UUIDs de país y fechas estandarizadas.
        
    # 🚨 ¿Por qué especificar `queue='ia_fast'`?: 
    # Arquitectura crítica. Como esta llamada la gatilla un humano frente a su pantalla/Alpine.js
    # esperando ver el input con el Extractor Visual rellenándose mágicamente, NO PUEDE
    # quedarse asfixiado en la cola Celery default detrás de un scrape masivo de 500 emails IMAP. 
    # Se enruta a workers reservados en RAM alta para latencia sub 1-second.
    """
    import base64

    from apps.automation.services.ocr_service import ocr_service
    
    try:
        logger.info("⚡ Iniciando tarea de OCR rápida para Pasaporte (IA_FAST)")
        content = base64.b64decode(file_content_base64)
        resultado = ocr_service.procesar_pasaporte(content, mime_type)
        return resultado
    except Exception as e:
        logger.error(f"❌ Error en task_ocr_passport_fast: {e}")
    
@tenant_task(
    name="core.tasks.migrar_logos_agencia_task",
    time_limit=600,
    soft_time_limit=540,
    max_retries=2,
    default_retry_delay=600,
)
def migrar_logos_agencia_task(agencia_id, **kwargs):
    """
    ⚡ ASÍNCRONO
    Migra logos de la base de datos (ImageField o Base64) a Telegram Storage
    para liberar espacio y optimizar la carga.
    """
    import base64
    from io import BytesIO

    from apps.communications.services.telegram_unified import upload_logo_to_telegram
    from core.models.agencia import Agencia
    
    try:
        agencia = Agencia.objects.get(pk=agencia_id)
    except Agencia.DoesNotExist:
        return f"Agencia {agencia_id} no encontrada."

    branding = agencia.branding
    if not branding:
        return f"Agencia {agencia_id} no tiene componente de branding."

    updated_fields = []

    # Caso 1: Nuevo Logo subido por Admin (FileField)
    if branding.logo and not branding.logo_telegram_id:
        try:
            fid = upload_logo_to_telegram(branding.logo.file, branding.logo.name)
            if fid:
                branding.logo_telegram_id = fid
                branding.logo_base64 = None
                updated_fields.extend(['logo_telegram_id', 'logo_base64'])
        except Exception as e:
            logger.error(f"Error subiendo logo a Telegram para Agencia {agencia_id}: {e}")

    # Caso 2: Logos en Base64
    logos_to_migrate = [
        ('logo_base64', 'logo_general'),
        ('logo_pdf_base64', 'logo_pdf_light'),
        ('logo_pdf_dark_base64', 'logo_pdf_dark')
    ]
    
    for field_name, prefix in logos_to_migrate:
        val = getattr(branding, field_name, None)
        if val and len(val) > 1000:
            try:
                if ';base64,' in val:
                    header, data = val.split(';base64,')
                else:
                    data = val
                
                decoded = base64.b64decode(data)
                fid = upload_logo_to_telegram(BytesIO(decoded), f"{prefix}_{agencia.rif or agencia.pk}.png")
                if fid:
                    if field_name == 'logo_base64':
                        branding.logo_telegram_id = fid
                        branding.logo_base64 = None
                        updated_fields.extend(['logo_telegram_id', 'logo_base64'])
            except Exception as e:
                logger.error(f"Error migrando {field_name} a Telegram para Agencia {agencia_id}: {e}")

    if updated_fields:
        branding.save(update_fields=list(set(updated_fields)))
        return f"Branding de Agencia {agencia_id} actualizado: {updated_fields}"
    

@shared_task(
    name="core.tasks.cleanup_temporary_storage_files",
    time_limit=300,
    soft_time_limit=270,
    max_retries=2,
    default_retry_delay=3600,
)
def cleanup_temporary_storage_files(days=7):
    """
    🏢 INFRAESTRUCTURA | ☁️ STORAGE
    Limpia archivos en prefijos temporales (temp/, tmp/) que tengan más de 'days' de antigüedad.
    Compatible con Cloudflare R2, S3 y Almacenamiento Local.
    """
    import datetime

    from django.core.files.storage import default_storage
    from django.utils import timezone

    logger.info(f"🧹 Iniciando limpieza de archivos temporales (Antigüedad > {days} días)...")
    
    prefixes = ['temp/', 'tmp/', 'vouchers_tmp/']
    count = 0
    deleted_size = 0
    
    threshold = timezone.now() - datetime.timedelta(days=days)

    for prefix in prefixes:
        try:
            # Listar archivos en el prefijo
            # Nota: Algunos backends de storage pueden no soportar directories() eficientemente,
            # pero default_storage.listdir es el estándar de Django.
            dirs, files = default_storage.listdir(prefix)
            
            for filename in files:
                filepath = os.path.join(prefix, filename)
                try:
                    # Obtener fecha de modificación
                    mtime = default_storage.get_modified_time(filepath)
                    
                    if mtime < threshold:
                        size = default_storage.size(filepath)
                        default_storage.delete(filepath)
                        count += 1
                        deleted_size += size
                        logger.debug(f"🗑️ Eliminado: {filepath} ({size} bytes)")
                except Exception as e:
                    logger.error(f"⚠️ No se pudo procesar/borrar {filepath}: {e}")
                    
        except Exception as e:
            logger.warning(f"⚠️ Error accediendo al prefijo {prefix}: {e}")

    result = f"Limpieza completada. Se eliminaron {count} archivos ({deleted_size / 1024:.2f} KB)."
    logger.info(result)
    return result


@shared_task(bind=True, max_retries=2, default_retry_delay=3600)
def backup_database_task(self):
    """Tarea Celery: ejecuta pg_dump diario y rota backups."""
    from django.core.management import call_command

    try:
        call_command("backup_database", retention_days=7)
        logger.info("Backup diario completado exitosamente")
        return "Backup completado"
    except Exception as exc:
        logger.error(f"Backup diario falló: {exc}")
        raise self.retry(exc=exc) from exc
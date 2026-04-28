# core/tasks.py
import imaplib
import email
from email.header import decode_header
import logging
import os

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile

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


@shared_task(name="core.tasks.process_incoming_emails")
def process_incoming_emails():
    """
    ⚡ ASÍNCRONO | 🏢 MULTI-TENANT
    Daemon orquestador tipo Cron que inspecciona los correos de todas las agencias activas buscando boletos para auto-parseo.
    
    ¿Por qué?: En un modelo SaaS, no podemos requerir procesos bloqueando el servidor HTTP esperando IMAP.
    Esta tarea se ejecuta silenciosamente. Usamos `process_all=False` para procesar por lotes (batches controlados) 
    y evitar crashes de memoria (OOM) si una agencia inunda repentinamente la bandeja con 10,000 correos atrasados.
    """
    from core.models import Agencia
    from core.services.email_monitor_service import EmailMonitorService

    logger.info("🚀 Iniciando tarea programada: Procesamiento de Correos (Multi-Tenant)")
    
    # SaaS: Buscar todas las agencias activas con configuración de correo
    agencias = Agencia.objects.filter(activa=True).exclude(correo_emisiones__isnull=True).exclude(correo_emisiones__exact='')
    total_procesados = 0
    total_agencias = 0

    if not agencias.exists():
        logger.warning("No hay agencias activas para monitorear.")
        return "Sin agencias activas."

    for agencia in agencias:
        try:
            # Validar si tiene credenciales SaaS configuradas
            if not agencia.correo_emisiones or not agencia.password_app_correo:
                continue

            logger.info(f"🔄 Procesando agencia SaaS: {agencia.nombre} ({agencia.correo_emisiones})")
            
            monitor = EmailMonitorService(
                agencia=agencia, 
                notification_type='telegram', # Changed to telegram to ensure Admin gets notified + backup email
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


@shared_task(name="core.tasks.parsear_boleto_individual")
def parsear_boleto_individual(boleto_id):
    """
    Tarea asíncrona para procesar un boleto individual.
    Útil para uploads desde Admin o reintentos manuales.
    """
    try:
        from core.services.ticket_parser_service import TicketParserService
        logger.info(f"🧩 Iniciando tarea de parseo para Boleto {boleto_id}")
        service = TicketParserService()
        resultado = service.procesar_boleto(boleto_id)
        if resultado:
             logger.info(f"✅ Tarea de parseo completada para Boleto {boleto_id}")
             return f"Boleto {boleto_id} procesado exitosamente."
        else:
             logger.warning(f"⚠️ Tarea de parseo finalizó sin resultados para Boleto {boleto_id}")
             return f"Fallo al procesar Boleto {boleto_id}"
    except Exception as e:
        logger.error(f"❌ Error en parsear_boleto_individual: {e}")
        return f"Error: {e}"


@shared_task(name="core.tasks.retry_queued_boletos")
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
    from .utils.celery_utils import safe_delay
    
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


    

    

    @shared_task(name="core.tasks.send_ticket_notification")

    def send_ticket_notification(boleto_id):

        """

        Envía una notificación por correo electrónico con el boleto PDF generado.

        """

        try:
            from apps.bookings.models import BoletoImportado
            boleto = BoletoImportado.objects.get(id_boleto_importado=boleto_id)

            logger.info(f"Iniciando envío de notificación para Boleto ID: {boleto_id}")

    

            if not boleto.archivo_pdf_generado:

                logger.warning(f"No se encontró PDF generado para el Boleto ID: {boleto_id}. No se puede enviar notificación.")

                return f"No hay PDF para el boleto {boleto_id}."

    

            # --- Lógica de envío de correo ---

            from django.core.mail import EmailMessage

    

            # SaaS Fix: Usar email de soporte/ventas de la agencia
            if not recipient_email:
                logger.error(f"Agencia {boleto.agencia.nombre} no tiene email configurado. No se puede enviar correo.")
                return "Destinatario de notificación no configurado."

            # 🛡️ Guard: Skip placeholder emails to avoid bounce-backs
            if "@sin-email.com" in recipient_email.lower():
                logger.info(f"🔕 Notificación omitida para email de marcador de posición: {recipient_email}")
                return "Omitido por ser email de marcador de posición"

    

            # SaaS Fix: Firma dinámica
            sender_name = boleto.agencia.nombre_comercial or boleto.agencia.nombre
            from_email = boleto.agencia.email_principal or settings.DEFAULT_FROM_EMAIL
            
            subject = f"Nuevo Boleto Procesado: {boleto.nombre_pasajero_procesado or 'N/A'} - PNR: {boleto.localizador_pnr or 'N/A'}"

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

                boleto.archivo_pdf_generado.name,

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

            # Reintentar la tarea podría ser una opción aquí si es un error de red

            raise e


@shared_task(name="core.tasks.check_passport_expiry")
def check_passport_expiry():
    """
    Tarea diaria para verificar pasaportes próximos a vencer (6 meses).
    Envía una alerta al agente (o cliente en el futuro).
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.crm.models import Pasajero, Cliente
    from django.core.mail import send_mail
    
    logger.info("Iniciando chequeo de vencimiento de documentos (Multi-Tenant)...")
    
    today = timezone.now().date()
    threshold_date = today + timedelta(days=180) # 6 meses
    
    # Buscar pasaportes que vencen en el rango de la semana objetivo
    start_range = threshold_date
    end_range = threshold_date + timedelta(days=7)
    
    from core.models import Agencia
    total_alerts = 0

    # Iterar por agencia para enviar reportes separados
    for agencia in Agencia.objects.filter(activa=True):
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


@shared_task(name="core.tasks.check_upcoming_flights")
def check_upcoming_flights():
    """
    🏢 MULTI-TENANT | ⚡ ASÍNCRONO
    Busca vuelos pautados para las próximas 24 horas y envía "Recordatorios de Check-In".
    
    ¿Por qué?: Valor agregado premium (Concierge mode). En vez de que el agente humano 
    revise reportes a mano en Excel para atender a sus clientes Vip, nuestro scraper 
    detecta los PNR críticos (que están marcados como Finalizados en el JSON estructurado)
    y alerta en el Grupo interno de Telegram. Así, el agente entra al GDS y factura antes.
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.bookings.models import BoletoImportado
    from core.utils.telegram_utils import send_telegram_alert_sync
    import json
    
    logger.info("🔍 Buscando vuelos próximos para Check-in...")
    
    now = timezone.now()
    tomorrow_start = now + timedelta(hours=23)
    tomorrow_end = now + timedelta(hours=25)
    
    # Buscamos boletos con fecha de salida en el rango de ~24hs
    # Nota: Esto depende de que hayamos parseado la fecha de salida.
    # Como el modelo BoletoImportado actual guarda mucha data en JSON, 
    # iteraremos los recientes para verificar la fecha dentro del JSON 'datos_parseados'.
    
    # Optimización: Filtrar por fecha de creación reciente (últimos 365 días)
    # y que no estén cancelados.
    from core.models import Agencia
    from core.services.telegram_notification_service import TelegramNotificationService
    
    total_alerts = 0
    
    # Iterar por Agencias
    for agencia in Agencia.objects.filter(activa=True):
        boletos = BoletoImportado.objects.filter(
            agencia=agencia,
            fecha_subida__gte=now - timedelta(days=365),
            estado_parseo='COM'
        )
        
        # Obtener Chat ID de la agencia (SaaS)
        chat_id = agencia.configuracion_api.get('TELEGRAM_GROUP_ID') or getattr(settings, 'TELEGRAM_GROUP_ID', None)
        if not chat_id: continue

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


@shared_task(name="core.tasks.check_client_birthdays")
def check_client_birthdays():
    """
    Tarea diaria para felicitar a clientes y pasajeros por su cumpleaños.
    Soporta configuración Multi-Tenant (SMTP por Agencia).
    """
    from django.utils import timezone
    from apps.crm.models import Cliente, Pasajero
    from core.models import Agencia
    from django.core.mail import get_connection, EmailMessage
    
    logger.info("Iniciando chequeo de cumpleaños (Multi-Tenant)...")
    today = timezone.now().date()
    count = 0
    
    # Iterar por cada agencia activa
    for agencia in Agencia.objects.filter(activa=True):
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


@shared_task(name="core.tasks.check_pending_payments")
def check_pending_payments():
    """
    Tarea diaria para recordar pagos pendientes.
    Regla: Recordar a los 3, 7 y 15 días de la venta si hay saldo pendiente.
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.bookings.models import Venta
    from django.core.mail import send_mail
    
    logger.info("Iniciando chequeo de pagos pendientes...")
    today = timezone.now().date()
    
    # Definir los días de antigüedad para enviar recordatorio
    days_to_remind = [3, 7, 15]
    
    count = 0
    
    from core.models import Agencia
    from django.core.mail import get_connection

    for agencia in Agencia.objects.filter(activa=True):
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
            except Exception:
                pass
        
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
                        f"Desde {sender_name} le recordamos que su reserva con localizador {venta.localizador} tiene un saldo pendiente de {venta.saldo_pendiente} {venta.moneda.codigo}.\n\n"
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


@shared_task(name="core.tasks.sync_bcv_rates")
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


@shared_task(name="core.tasks.enviar_notificacion_whatsapp_task", bind=True, max_retries=3)
def enviar_notificacion_whatsapp_task(self, numero_cliente, mensaje, email_cliente=None, agencia_nombre="TravelHub"):
    """
    🚨 CRÍTICO | ⚡ ASÍNCRONO
    Patrón Resiliente con Dead Letter Queue para envíos por Meta API (WhatsApp).
    
    Args:
        numero_cliente (str): Teléfono destinatario.
        mensaje (str): Cuerpo estructurado (Jinja2 render renderizado usualmente).
        email_cliente (str, optional): Correo de emergencia si todo falla.
        agencia_nombre (str): Nombre SaaS a inyectar en fallbacks.
        
    # ¿Por qué Backoff Escalonado (300s, 900s, 3600s)?: 
    # La API Cloud de WhatsApp penaliza/banea números Tiers si hacemos force-retry infinito cuando 
    # fallan por saturación de red GDS. Esperamos pragmáticamente entre intentos.
    
    # ¿Por qué Fallback Dual Definitivo (Email + Telegram)?: 
    # Si tras 4 horas de pelear con Meta no se envió el WS, TravelHub tiene *responsabilidad civil* 
    # de advertir de cambios de itinerario. Enviamos SMTP pasivo al cliente, y alertamos con sirenas (Telegram) 
    # al Agente SaaS para que levante el teléfono y contacte manualmente al pasajero.
    """
    from django.core.mail import send_mail
    from core.services.telegram_service import enviar_alerta_telegram
    from core.services.whatsapp_service import enviar_mensaje_meta_api 

    try:
        # 1. INTENTO PRINCIPAL: Enviar por la API de WhatsApp Cloud (Meta)
        logger.info(f"Intentando enviar WhatsApp a {numero_cliente} (Intento {self.request.retries + 1}/4)")
        
        respuesta = enviar_mensaje_meta_api(numero_cliente, mensaje)
        
        # Validamos si Meta devolvió un error (ej. cliente sin WhatsApp o API caída)
        if not respuesta.get('success'):
            raise Exception(f"Meta API Error: {respuesta.get('error_message', 'Unknown Error')}")
            
        logger.info(f"✅ WhatsApp enviado exitosamente a {numero_cliente}")
        return "Notificación enviada"

    except Exception as exc:
        # 2. SISTEMA DE REINTENTOS ESCALONADOS (Retry Backoff)
        # Tiempos en segundos: 5 min (300s), 15 min (900s), 1 hora (3600s)
        retrasos_escalonados = [300, 900, 3600] 
        
        if self.request.retries < self.max_retries:
            tiempo_espera = retrasos_escalonados[self.request.retries]
            logger.warning(f"⚠️ Fallo WhatsApp a {numero_cliente}. Reintentando en {tiempo_espera/60} minutos... Error: {str(exc)}")
            
            # Reprogramamos la tarea para que vuelva a la cola de Redis y espere
            raise self.retry(exc=exc, countdown=tiempo_espera)
            
        else:
            # 3. DEAD LETTER QUEUE (FALLBACK DEFINITIVO)
            # Ya fallaron los 4 intentos (1 original + 3 retries). Activamos el Plan B.
            logger.error(f"❌ Fallo definitivo enviando WhatsApp a {numero_cliente}. Ejecutando Fallback (Email + Telegram).")
            
            # A. Notificar al Agente de Viajes por Telegram (Para que llame al cliente si es urgente)
            alerta_agencia = (
                f"🚨 *ALERTA DE COMUNICACIÓN - {agencia_nombre}*\n\n"
                f"No pudimos entregar un WhatsApp al cliente *{numero_cliente}* "
                f"después de 4 intentos.\n"
                f"Motivo: API de Meta inaccesible o número inválido.\n"
                f"🛡️ *Se ha enviado un correo de respaldo al cliente.*"
            )
            enviar_alerta_telegram(alerta_agencia)
            
            # B. Enviar correo de respaldo (SMTP) al cliente
            if email_cliente:
                try:
                    send_mail(
                        subject=f"Tu Itinerario de Vuelo (Respaldo) - {agencia_nombre}",
                        message=f"Hola,\n\nIntentamos contactarte por WhatsApp pero tuvimos un problema técnico con la plataforma. Aquí te enviamos tu información importante:\n\n{mensaje}\n\nSaludos,\nEl equipo de {agencia_nombre}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email_cliente],
                        fail_silently=True
                    )
                    logger.info(f"📧 Correo de respaldo enviado a {email_cliente}")
                except Exception as mail_exc:
                    logger.error(f"Fallo doble: Tampoco se pudo enviar el correo de respaldo. Error: {str(mail_exc)}")
            
            return "Fallo definitivo - Plan B ejecutado"


@shared_task(name="core.tasks.task_ocr_passport_fast", queue='ia_fast')
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
    from core.services.ocr_service import ocr_service
    
    try:
        logger.info(f"⚡ Iniciando tarea de OCR rápida para Pasaporte (IA_FAST)")
        content = base64.b64decode(file_content_base64)
        resultado = ocr_service.procesar_pasaporte(content, mime_type)
        return resultado
    except Exception as e:
        logger.error(f"❌ Error en task_ocr_passport_fast: {e}")
    
@shared_task(name="core.tasks.migrar_logos_agencia_task")
def migrar_logos_agencia_task(agencia_id):
    """
    ⚡ ASÍNCRONO
    Migra logos de la base de datos (ImageField o Base64) a Telegram Storage
    para liberar espacio y optimizar la carga.
    """
    from core.models import Agencia
    from core.utils.telegram_storage import upload_logo_to_telegram
    import base64
    from io import BytesIO
    
    try:
        agencia = Agencia.objects.get(pk=agencia_id)
    except Agencia.DoesNotExist:
        return f"Agencia {agencia_id} no encontrada."

    updated_fields = []

    # Caso 1: Nuevo Logo subido por Admin (FileField)
    if agencia.logo and not agencia.logo_telegram_id:
        try:
            fid = upload_logo_to_telegram(agencia.logo.file, agencia.logo.name)
            if fid:
                agencia.logo_telegram_id = fid
                agencia.logo_base64 = None
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
        val = getattr(agencia, field_name)
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
                        agencia.logo_telegram_id = fid
                        agencia.logo_base64 = None
                        updated_fields.extend(['logo_telegram_id', 'logo_base64'])
            except Exception as e:
                logger.error(f"Error migrando {field_name} a Telegram para Agencia {agencia_id}: {e}")

    if updated_fields:
        agencia.save(update_fields=list(set(updated_fields)))
        return f"Agencia {agencia_id} actualizada: {updated_fields}"
    
    return f"Agencia {agencia_id} no requería migración."


    